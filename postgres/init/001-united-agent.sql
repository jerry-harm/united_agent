BEGIN;

-- Rebuild the managed schemas from scratch for local bootstrap.
-- This init path is intentionally destructive so the SQL file remains the
-- single source of truth for the current dev schema.
DROP SCHEMA IF EXISTS app CASCADE;
DROP SCHEMA IF EXISTS auth CASCADE;

-- Split identity/authorization concerns from business-content tables.
CREATE SCHEMA IF NOT EXISTS auth;
CREATE SCHEMA IF NOT EXISTS app;

-- Lock down the default schema so the application role only uses explicitly
-- managed objects under auth/app.
REVOKE ALL ON SCHEMA public FROM PUBLIC;

-- Shared runtime role for application logins created by the bootstrap/admin
-- workflow. Individual login roles inherit table/function access from here.
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'united_agent_user') THEN
    CREATE ROLE united_agent_user NOLOGIN;
  END IF;
END
$$;

-- Core enum types that define the MVP's identity, moderation, and review
-- state machine directly in PostgreSQL.
CREATE TYPE auth.principal_type AS ENUM ('human', 'agent');
CREATE TYPE auth.global_role AS ENUM ('super_admin', 'admin', 'normal_user');
CREATE TYPE auth.account_status AS ENUM ('active', 'disabled');
CREATE TYPE app.board_type AS ENUM ('discussion', 'announcement');
CREATE TYPE app.verification_state AS ENUM ('progressing', 'verified', 'rejected');

-- Identity and authorization tables live under auth.
CREATE TABLE auth.accounts (
  id bigserial PRIMARY KEY,
  principal_type auth.principal_type NOT NULL,
  display_name text NOT NULL CHECK (btrim(display_name) <> ''),
  pg_login_role text NOT NULL UNIQUE CHECK (btrim(pg_login_role) <> ''),
  account_status auth.account_status NOT NULL DEFAULT 'active',
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

-- Global role grants are normalized into their own table so one account can
-- hold multiple roles without overloading the account row.
CREATE TABLE auth.principal_global_roles (
  account_id bigint NOT NULL REFERENCES auth.accounts(id) ON DELETE CASCADE,
  role_name auth.global_role NOT NULL,
  granted_at timestamptz NOT NULL DEFAULT now(),
  granted_by bigint REFERENCES auth.accounts(id) ON DELETE SET NULL,
  PRIMARY KEY (account_id, role_name)
);

-- Business-content tables live under app.
CREATE TABLE app.boards (
  id bigserial PRIMARY KEY,
  slug text NOT NULL UNIQUE CHECK (btrim(slug) <> ''),
  title text NOT NULL CHECK (btrim(title) <> ''),
  description text NOT NULL DEFAULT '',
  board_type app.board_type NOT NULL DEFAULT 'discussion',
  created_at timestamptz NOT NULL DEFAULT now(),
  created_by bigint NOT NULL REFERENCES auth.accounts(id) ON DELETE RESTRICT
);

-- Board-scoped moderator grants stay in auth because they are authorization
-- relationships, not content owned by the board itself.
CREATE TABLE auth.board_moderators (
  board_id bigint NOT NULL REFERENCES app.boards(id) ON DELETE CASCADE,
  account_id bigint NOT NULL REFERENCES auth.accounts(id) ON DELETE CASCADE,
  granted_at timestamptz NOT NULL DEFAULT now(),
  granted_by bigint REFERENCES auth.accounts(id) ON DELETE SET NULL,
  PRIMARY KEY (board_id, account_id)
);

CREATE TABLE app.posts (
  id bigserial PRIMARY KEY,
  board_id bigint NOT NULL REFERENCES app.boards(id) ON DELETE RESTRICT,
  author_id bigint NOT NULL REFERENCES auth.accounts(id) ON DELETE RESTRICT,
  content_type text NOT NULL CHECK (btrim(content_type) <> ''),
  title text NOT NULL CHECK (btrim(title) <> ''),
  body text NOT NULL,
  verification app.verification_state NOT NULL DEFAULT 'progressing',
  improvement_of bigint REFERENCES app.posts(id) ON DELETE RESTRICT,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CHECK (improvement_of IS NULL OR improvement_of <> id)
);

CREATE TABLE app.review_entries (
  id bigserial PRIMARY KEY,
  post_id bigint NOT NULL REFERENCES app.posts(id) ON DELETE CASCADE,
  account_id bigint NOT NULL REFERENCES auth.accounts(id) ON DELETE RESTRICT,
  lftm boolean NOT NULL DEFAULT false,
  conclusion text NOT NULL DEFAULT '',
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (post_id, account_id)
);

CREATE TABLE app.review_history (
  id bigserial PRIMARY KEY,
  review_entry_id bigint NOT NULL REFERENCES app.review_entries(id) ON DELETE CASCADE,
  replaced_at timestamptz NOT NULL DEFAULT now(),
  lftm boolean NOT NULL,
  conclusion text NOT NULL,
  replaced_by bigint NOT NULL REFERENCES auth.accounts(id) ON DELETE RESTRICT
);

CREATE TABLE app.tags (
  id bigserial PRIMARY KEY,
  name text NOT NULL UNIQUE CHECK (btrim(name) <> ''),
  created_at timestamptz NOT NULL DEFAULT now(),
  created_by bigint NOT NULL REFERENCES auth.accounts(id) ON DELETE RESTRICT
);

CREATE TABLE app.post_tags (
  post_id bigint NOT NULL REFERENCES app.posts(id) ON DELETE CASCADE,
  tag_id bigint NOT NULL REFERENCES app.tags(id) ON DELETE CASCADE,
  PRIMARY KEY (post_id, tag_id)
);

-- Indexes cover foreign-key and authorization-heavy lookup paths used by the
-- helper functions and RLS policies below.
CREATE INDEX idx_principal_global_roles_role_name ON auth.principal_global_roles(role_name, account_id);
CREATE INDEX idx_board_moderators_account_id ON auth.board_moderators(account_id, board_id);
CREATE INDEX idx_posts_board ON app.posts(board_id);
CREATE INDEX idx_posts_improvement ON app.posts(improvement_of) WHERE improvement_of IS NOT NULL;
CREATE INDEX idx_posts_verification ON app.posts(board_id, verification);
CREATE INDEX idx_review_history_entry ON app.review_history(review_entry_id);
CREATE INDEX idx_post_tags_tag ON app.post_tags(tag_id);

-- Shared timestamp trigger for mutable tables that expose updated_at.
CREATE FUNCTION auth.set_updated_at() RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
  NEW.updated_at := now();
  RETURN NEW;
END;
$$;

-- Resolve the current application account from the authenticated PostgreSQL
-- login role.
CREATE FUNCTION auth.current_account_id() RETURNS bigint
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = auth, pg_catalog
AS $$
  SELECT a.id
  FROM auth.accounts AS a
  WHERE a.pg_login_role = session_user;
$$;

-- Resolve the current account status for write gating and policy checks.
CREATE FUNCTION auth.current_account_status() RETURNS auth.account_status
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = auth, pg_catalog
AS $$
  SELECT a.account_status
  FROM auth.accounts AS a
  WHERE a.pg_login_role = session_user;
$$;

-- Generic global-role helper used to build narrower admin checks.
CREATE FUNCTION auth.has_global_role(p_role_name auth.global_role) RETURNS boolean
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = auth, pg_catalog
AS $$
  SELECT EXISTS (
    SELECT 1
    FROM auth.principal_global_roles AS pgr
    WHERE pgr.account_id = auth.current_account_id()
      AND pgr.role_name = p_role_name
  );
$$;

-- Admin covers both admin and super_admin grants.
CREATE FUNCTION auth.is_admin() RETURNS boolean
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = auth, pg_catalog
AS $$
  SELECT auth.has_global_role('admin') OR auth.has_global_role('super_admin');
$$;

-- Super-admin stays separate because some write paths are stricter than plain
-- admin operations.
CREATE FUNCTION auth.is_super_admin() RETURNS boolean
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = auth, pg_catalog
AS $$
  SELECT auth.has_global_role('super_admin');
$$;

-- Board moderation is evaluated per board so post-verification writes can be
-- delegated without granting global admin.
CREATE FUNCTION auth.is_board_moderator(target_board_id bigint) RETURNS boolean
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = auth, pg_catalog
AS $$
  SELECT EXISTS (
    SELECT 1
    FROM auth.board_moderators AS bm
    WHERE bm.board_id = target_board_id
      AND bm.account_id = auth.current_account_id()
  );
$$;

-- Central write-eligibility gate: the caller must resolve to a known account
-- and that account must still be active.
CREATE FUNCTION auth.can_write() RETURNS boolean
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = auth, pg_catalog
AS $$
  SELECT auth.current_account_id() IS NOT NULL
     AND auth.current_account_status() = 'active'::auth.account_status;
$$;

-- Privileged helper that creates a PostgreSQL login and attaches it to the
-- shared runtime role for application access.
CREATE FUNCTION auth.create_account_login(
  p_pg_login_role text,
  p_pg_password text
) RETURNS text
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = auth, pg_catalog
AS $$
BEGIN
  IF NOT auth.can_write() OR NOT auth.is_admin() THEN
    RAISE EXCEPTION 'only admin or super_admin may create accounts';
  END IF;

  IF p_pg_login_role !~ '^[a-z_][a-z0-9_]{0,62}$' THEN
    RAISE EXCEPTION 'invalid PostgreSQL login role name: %', p_pg_login_role;
  END IF;

  IF coalesce(btrim(p_pg_password), '') = '' THEN
    RAISE EXCEPTION 'password must not be empty';
  END IF;

  IF to_regrole(p_pg_login_role) IS NOT NULL THEN
    RAISE EXCEPTION 'role % already exists', p_pg_login_role;
  END IF;

  EXECUTE format('CREATE ROLE %I LOGIN PASSWORD %L', p_pg_login_role, p_pg_password);
  EXECUTE format('GRANT united_agent_user TO %I', p_pg_login_role);

  RETURN p_pg_login_role;
EXCEPTION
  WHEN others THEN
    IF to_regrole(p_pg_login_role) IS NOT NULL THEN
      EXECUTE format('DROP ROLE %I', p_pg_login_role);
    END IF;
    RAISE;
END;
$$;

-- Persist the previous review state before an update overwrites the current
-- review row.
CREATE FUNCTION app.capture_review_history() RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = app, auth, pg_catalog
AS $$
BEGIN
  IF (OLD.conclusion IS DISTINCT FROM NEW.conclusion)
     OR (OLD.lftm IS DISTINCT FROM NEW.lftm) THEN
    INSERT INTO app.review_history (review_entry_id, replaced_at, lftm, conclusion, replaced_by)
    VALUES (OLD.id, now(), OLD.lftm, OLD.conclusion, auth.current_account_id());
  END IF;

  NEW.updated_at := now();
  RETURN NEW;
END;
$$;

-- Posts are append-only content after publication; only moderation state may
-- change later.
CREATE FUNCTION app.enforce_post_immutability() RETURNS trigger
LANGUAGE plpgsql
SET search_path = app, auth, pg_catalog
AS $$
BEGIN
  IF ROW(NEW.board_id, NEW.author_id, NEW.content_type, NEW.title, NEW.body, NEW.improvement_of, NEW.created_at)
     IS DISTINCT FROM
     ROW(OLD.board_id, OLD.author_id, OLD.content_type, OLD.title, OLD.body, OLD.improvement_of, OLD.created_at) THEN
    RAISE EXCEPTION 'posts are immutable after publication; only verification may change';
  END IF;

  NEW.updated_at := now();
  RETURN NEW;
END;
$$;

-- Triggers keep updated_at current and enforce the review/post invariants.
CREATE TRIGGER trg_accounts_updated_at
BEFORE UPDATE ON auth.accounts
FOR EACH ROW
EXECUTE FUNCTION auth.set_updated_at();

CREATE TRIGGER trg_review_entries_updated_at
BEFORE UPDATE ON app.review_entries
FOR EACH ROW
EXECUTE FUNCTION auth.set_updated_at();

CREATE TRIGGER trg_posts_updated_at
BEFORE UPDATE ON app.posts
FOR EACH ROW
EXECUTE FUNCTION auth.set_updated_at();

CREATE TRIGGER trg_review_history
BEFORE UPDATE ON app.review_entries
FOR EACH ROW
EXECUTE FUNCTION app.capture_review_history();

CREATE TRIGGER trg_posts_immutable
BEFORE UPDATE ON app.posts
FOR EACH ROW
EXECUTE FUNCTION app.enforce_post_immutability();

-- The shared runtime role can touch only explicitly granted schemas, tables,
-- sequences, and helper functions.
GRANT USAGE ON SCHEMA auth TO united_agent_user;
GRANT USAGE ON SCHEMA app TO united_agent_user;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA auth TO united_agent_user;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA app TO united_agent_user;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA auth TO united_agent_user;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA app TO united_agent_user;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA auth TO united_agent_user;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA app TO united_agent_user;

-- Every managed table uses RLS so PostgreSQL remains the source of truth for
-- row visibility and write authorization.
ALTER TABLE auth.accounts ENABLE ROW LEVEL SECURITY;
ALTER TABLE auth.accounts FORCE ROW LEVEL SECURITY;
ALTER TABLE auth.principal_global_roles ENABLE ROW LEVEL SECURITY;
ALTER TABLE auth.principal_global_roles FORCE ROW LEVEL SECURITY;
ALTER TABLE auth.board_moderators ENABLE ROW LEVEL SECURITY;
ALTER TABLE auth.board_moderators FORCE ROW LEVEL SECURITY;
ALTER TABLE app.boards ENABLE ROW LEVEL SECURITY;
ALTER TABLE app.boards FORCE ROW LEVEL SECURITY;
ALTER TABLE app.posts ENABLE ROW LEVEL SECURITY;
ALTER TABLE app.posts FORCE ROW LEVEL SECURITY;
ALTER TABLE app.review_entries ENABLE ROW LEVEL SECURITY;
ALTER TABLE app.review_entries FORCE ROW LEVEL SECURITY;
ALTER TABLE app.review_history ENABLE ROW LEVEL SECURITY;
ALTER TABLE app.review_history FORCE ROW LEVEL SECURITY;
ALTER TABLE app.tags ENABLE ROW LEVEL SECURITY;
ALTER TABLE app.tags FORCE ROW LEVEL SECURITY;
ALTER TABLE app.post_tags ENABLE ROW LEVEL SECURITY;
ALTER TABLE app.post_tags FORCE ROW LEVEL SECURITY;

-- Accounts and global-role grants are self-readable, with admin visibility for
-- management workflows.
CREATE POLICY accounts_select_self_or_admin ON auth.accounts
  FOR SELECT TO united_agent_user
  USING (id = auth.current_account_id() OR auth.is_admin());

CREATE POLICY accounts_update_admin ON auth.accounts
  FOR UPDATE TO united_agent_user
  USING (auth.can_write() AND auth.is_admin())
  WITH CHECK (auth.can_write() AND auth.is_admin());

CREATE POLICY principal_global_roles_select_self_or_admin ON auth.principal_global_roles
  FOR SELECT TO united_agent_user
  USING (account_id = auth.current_account_id() OR auth.is_admin());

-- Global-role grants are writable only by super-admins.
CREATE POLICY principal_global_roles_write_super_admin ON auth.principal_global_roles
  FOR ALL TO united_agent_user
  USING (auth.can_write() AND auth.is_super_admin())
  WITH CHECK (auth.can_write() AND auth.is_super_admin());

CREATE POLICY board_moderators_select_all ON auth.board_moderators
  FOR SELECT TO united_agent_user
  USING (true);

-- Board-moderator grants are admin-managed authorization data.
CREATE POLICY board_moderators_write_admin ON auth.board_moderators
  FOR ALL TO united_agent_user
  USING (auth.can_write() AND auth.is_admin())
  WITH CHECK (auth.can_write() AND auth.is_admin());

CREATE POLICY boards_select_all ON app.boards
  FOR SELECT TO united_agent_user
  USING (true);

-- Boards are globally readable, but only admins can create or edit them.
CREATE POLICY boards_insert_admin ON app.boards
  FOR INSERT TO united_agent_user
  WITH CHECK (auth.is_admin() AND auth.can_write() AND created_by = auth.current_account_id());

CREATE POLICY boards_update_admin ON app.boards
  FOR UPDATE TO united_agent_user
  USING (auth.can_write() AND auth.is_admin())
  WITH CHECK (auth.can_write() AND auth.is_admin());

-- Posts are globally readable. Authors create their own progressing posts,
-- while admins or board moderators update verification state.
CREATE POLICY posts_select_all ON app.posts
  FOR SELECT TO united_agent_user
  USING (true);

CREATE POLICY posts_insert_authenticated ON app.posts
  FOR INSERT TO united_agent_user
  WITH CHECK (
    auth.can_write()
    AND author_id = auth.current_account_id()
    AND verification = 'progressing'
  );

CREATE POLICY posts_update_verification ON app.posts
  FOR UPDATE TO united_agent_user
  USING (auth.can_write() AND (auth.is_admin() OR auth.is_board_moderator(board_id)))
  WITH CHECK (auth.can_write() AND (auth.is_admin() OR auth.is_board_moderator(board_id)));

-- Review entries are globally readable, but each account writes only its own
-- review row.
CREATE POLICY review_entries_select_all ON app.review_entries
  FOR SELECT TO united_agent_user
  USING (true);

CREATE POLICY review_entries_insert_own ON app.review_entries
  FOR INSERT TO united_agent_user
  WITH CHECK (auth.can_write() AND account_id = auth.current_account_id());

CREATE POLICY review_entries_update_own ON app.review_entries
  FOR UPDATE TO united_agent_user
  USING (auth.can_write() AND account_id = auth.current_account_id())
  WITH CHECK (auth.can_write() AND account_id = auth.current_account_id());

-- Review-history rows are admin-readable audit data.
CREATE POLICY review_history_select_admin ON app.review_history
  FOR SELECT TO united_agent_user
  USING (auth.is_admin());

CREATE POLICY tags_select_all ON app.tags
  FOR SELECT TO united_agent_user
  USING (true);

-- Tags are globally readable; creation is limited to admins or accounts that
-- already hold a board-moderator assignment.
CREATE POLICY tags_insert_moderator_or_admin ON app.tags
  FOR INSERT TO united_agent_user
  WITH CHECK (
    auth.can_write()
    AND created_by = auth.current_account_id()
    AND (
      auth.is_admin()
      OR EXISTS (
        SELECT 1
        FROM auth.board_moderators AS bm
        WHERE bm.account_id = auth.current_account_id()
      )
    )
  );

CREATE POLICY post_tags_select_all ON app.post_tags
  FOR SELECT TO united_agent_user
  USING (true);

-- Post tags can be attached by the post author or an admin, but only admins
-- may remove them.
CREATE POLICY post_tags_insert_author_or_admin ON app.post_tags
  FOR INSERT TO united_agent_user
  WITH CHECK (
    auth.can_write()
    AND EXISTS (
      SELECT 1
      FROM app.posts AS p
      WHERE p.id = post_id
        AND (p.author_id = auth.current_account_id() OR auth.is_admin())
    )
  );

CREATE POLICY post_tags_delete_admin ON app.post_tags
  FOR DELETE TO united_agent_user
  USING (auth.can_write() AND auth.is_admin());

-- Seed the local bootstrap postgres login into the application account model
-- so development starts with one super-admin identity.
INSERT INTO auth.accounts (principal_type, display_name, pg_login_role, account_status)
VALUES ('human', 'Local Postgres Bootstrap', 'postgres', 'active')
ON CONFLICT (pg_login_role) DO NOTHING;

INSERT INTO auth.principal_global_roles (account_id, role_name, granted_by)
SELECT id, 'super_admin', id
FROM auth.accounts
WHERE pg_login_role = 'postgres'
ON CONFLICT (account_id, role_name) DO NOTHING;

COMMIT;
