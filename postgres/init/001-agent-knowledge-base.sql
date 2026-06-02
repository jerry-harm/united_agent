BEGIN;

CREATE SCHEMA IF NOT EXISTS app;

DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'agent_kb_user') THEN
    CREATE ROLE agent_kb_user NOLOGIN;
  END IF;
END
$$;

CREATE TYPE app.principal_type AS ENUM ('human', 'agent');
CREATE TYPE app.business_role AS ENUM ('super_admin', 'admin', 'normal_user');
CREATE TYPE app.board_type AS ENUM ('discussion', 'announcement');
CREATE TYPE app.verification_state AS ENUM ('progressing', 'verified', 'rejected');

CREATE TABLE app.principals (
  id bigserial PRIMARY KEY,
  principal_type app.principal_type NOT NULL,
  display_name text NOT NULL CHECK (btrim(display_name) <> ''),
  business_role app.business_role NOT NULL,
  pg_login_role text NOT NULL UNIQUE CHECK (btrim(pg_login_role) <> ''),
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE app.boards (
  id bigserial PRIMARY KEY,
  slug text NOT NULL UNIQUE CHECK (btrim(slug) <> ''),
  title text NOT NULL CHECK (btrim(title) <> ''),
  description text NOT NULL DEFAULT '',
  board_type app.board_type NOT NULL DEFAULT 'discussion',
  created_at timestamptz NOT NULL DEFAULT now(),
  created_by bigint NOT NULL REFERENCES app.principals(id)
);

CREATE TABLE app.board_moderators (
  board_id bigint NOT NULL REFERENCES app.boards(id) ON DELETE CASCADE,
  principal_id bigint NOT NULL REFERENCES app.principals(id) ON DELETE CASCADE,
  granted_at timestamptz NOT NULL DEFAULT now(),
  granted_by bigint REFERENCES app.principals(id),
  PRIMARY KEY (board_id, principal_id)
);

CREATE TABLE app.posts (
  id bigserial PRIMARY KEY,
  board_id bigint NOT NULL REFERENCES app.boards(id) ON DELETE RESTRICT,
  author_id bigint NOT NULL REFERENCES app.principals(id) ON DELETE RESTRICT,
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
  principal_id bigint NOT NULL REFERENCES app.principals(id) ON DELETE RESTRICT,
  lftm boolean NOT NULL DEFAULT false,
  conclusion text NOT NULL DEFAULT '',
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (post_id, principal_id)
);

CREATE TABLE app.review_history (
  id bigserial PRIMARY KEY,
  review_entry_id bigint NOT NULL REFERENCES app.review_entries(id) ON DELETE CASCADE,
  replaced_at timestamptz NOT NULL DEFAULT now(),
  lftm boolean NOT NULL,
  conclusion text NOT NULL,
  replaced_by bigint NOT NULL REFERENCES app.principals(id) ON DELETE RESTRICT
);

CREATE TABLE app.tags (
  id bigserial PRIMARY KEY,
  name text NOT NULL UNIQUE CHECK (btrim(name) <> ''),
  created_at timestamptz NOT NULL DEFAULT now(),
  created_by bigint NOT NULL REFERENCES app.principals(id) ON DELETE RESTRICT
);

CREATE TABLE app.post_tags (
  post_id bigint NOT NULL REFERENCES app.posts(id) ON DELETE CASCADE,
  tag_id bigint NOT NULL REFERENCES app.tags(id) ON DELETE CASCADE,
  PRIMARY KEY (post_id, tag_id)
);

CREATE INDEX idx_posts_board ON app.posts(board_id);
CREATE INDEX idx_posts_improvement ON app.posts(improvement_of) WHERE improvement_of IS NOT NULL;
CREATE INDEX idx_posts_verification ON app.posts(board_id, verification);
CREATE INDEX idx_review_history_entry ON app.review_history(review_entry_id);
CREATE INDEX idx_post_tags_tag ON app.post_tags(tag_id);

CREATE FUNCTION app.set_updated_at() RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
  NEW.updated_at := now();
  RETURN NEW;
END;
$$;

CREATE FUNCTION app.current_principal_id() RETURNS bigint
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = app, public
AS $$
  SELECT p.id
  FROM app.principals AS p
  WHERE p.pg_login_role = session_user;
$$;

CREATE FUNCTION app.current_business_role() RETURNS app.business_role
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = app, public
AS $$
  SELECT p.business_role
  FROM app.principals AS p
  WHERE p.pg_login_role = session_user;
$$;

CREATE FUNCTION app.is_board_moderator(target_board_id bigint) RETURNS boolean
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = app, public
AS $$
  SELECT EXISTS (
    SELECT 1
    FROM app.board_moderators AS bm
    WHERE bm.board_id = target_board_id
      AND bm.principal_id = app.current_principal_id()
  );
$$;

CREATE FUNCTION app.bootstrap_principal(
  p_principal_type app.principal_type,
  p_display_name text,
  p_business_role app.business_role,
  p_pg_login_role text,
  p_pg_password text
) RETURNS app.principals
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = app, public
AS $$
DECLARE
  created_principal app.principals;
BEGIN
  IF app.current_business_role() IS DISTINCT FROM 'super_admin'::app.business_role
     AND app.current_business_role() IS DISTINCT FROM 'admin'::app.business_role THEN
    RAISE EXCEPTION 'only admins may bootstrap principals';
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
  EXECUTE format('GRANT agent_kb_user TO %I', p_pg_login_role);

  INSERT INTO app.principals (principal_type, display_name, business_role, pg_login_role)
  VALUES (p_principal_type, p_display_name, p_business_role, p_pg_login_role)
  RETURNING * INTO created_principal;

  RETURN created_principal;
EXCEPTION
  WHEN others THEN
    IF to_regrole(p_pg_login_role) IS NOT NULL THEN
      EXECUTE format('DROP ROLE %I', p_pg_login_role);
    END IF;
    RAISE;
END;
$$;

CREATE FUNCTION app.capture_review_history() RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = app, public
AS $$
BEGIN
  IF (OLD.conclusion IS DISTINCT FROM NEW.conclusion)
     OR (OLD.lftm IS DISTINCT FROM NEW.lftm) THEN
    INSERT INTO app.review_history (review_entry_id, replaced_at, lftm, conclusion, replaced_by)
    VALUES (OLD.id, now(), OLD.lftm, OLD.conclusion, app.current_principal_id());
  END IF;

  NEW.updated_at := now();
  RETURN NEW;
END;
$$;

CREATE FUNCTION app.enforce_post_immutability() RETURNS trigger
LANGUAGE plpgsql
SET search_path = app, public
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

CREATE TRIGGER trg_principals_updated_at
BEFORE UPDATE ON app.principals
FOR EACH ROW
EXECUTE FUNCTION app.set_updated_at();

CREATE TRIGGER trg_review_entries_updated_at
BEFORE UPDATE ON app.review_entries
FOR EACH ROW
EXECUTE FUNCTION app.set_updated_at();

CREATE TRIGGER trg_review_history
BEFORE UPDATE ON app.review_entries
FOR EACH ROW
EXECUTE FUNCTION app.capture_review_history();

CREATE TRIGGER trg_posts_immutable
BEFORE UPDATE ON app.posts
FOR EACH ROW
EXECUTE FUNCTION app.enforce_post_immutability();

GRANT USAGE ON SCHEMA app TO agent_kb_user;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA app TO agent_kb_user;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA app TO agent_kb_user;

ALTER TABLE app.principals ENABLE ROW LEVEL SECURITY;
ALTER TABLE app.boards ENABLE ROW LEVEL SECURITY;
ALTER TABLE app.board_moderators ENABLE ROW LEVEL SECURITY;
ALTER TABLE app.posts ENABLE ROW LEVEL SECURITY;
ALTER TABLE app.review_entries ENABLE ROW LEVEL SECURITY;
ALTER TABLE app.review_history ENABLE ROW LEVEL SECURITY;
ALTER TABLE app.tags ENABLE ROW LEVEL SECURITY;
ALTER TABLE app.post_tags ENABLE ROW LEVEL SECURITY;

CREATE POLICY principals_select_all ON app.principals
  FOR SELECT TO agent_kb_user
  USING (true);

CREATE POLICY principals_update_admin ON app.principals
  FOR UPDATE TO agent_kb_user
  USING (app.current_business_role() IN ('super_admin', 'admin'))
  WITH CHECK (app.current_business_role() IN ('super_admin', 'admin'));

CREATE POLICY boards_select_all ON app.boards
  FOR SELECT TO agent_kb_user
  USING (true);

CREATE POLICY boards_insert_admin ON app.boards
  FOR INSERT TO agent_kb_user
  WITH CHECK (
    app.current_business_role() IN ('super_admin', 'admin')
    AND created_by = app.current_principal_id()
  );

CREATE POLICY boards_update_admin ON app.boards
  FOR UPDATE TO agent_kb_user
  USING (app.current_business_role() IN ('super_admin', 'admin'))
  WITH CHECK (app.current_business_role() IN ('super_admin', 'admin'));

CREATE POLICY board_moderators_select_all ON app.board_moderators
  FOR SELECT TO agent_kb_user
  USING (true);

CREATE POLICY board_moderators_write_admin ON app.board_moderators
  FOR ALL TO agent_kb_user
  USING (app.current_business_role() IN ('super_admin', 'admin'))
  WITH CHECK (app.current_business_role() IN ('super_admin', 'admin'));

CREATE POLICY posts_select_all ON app.posts
  FOR SELECT TO agent_kb_user
  USING (true);

CREATE POLICY posts_insert_authenticated ON app.posts
  FOR INSERT TO agent_kb_user
  WITH CHECK (
    author_id = app.current_principal_id()
    AND verification = 'progressing'
  );

CREATE POLICY posts_update_verification ON app.posts
  FOR UPDATE TO agent_kb_user
  USING (
    app.current_business_role() IN ('super_admin', 'admin')
    OR app.is_board_moderator(board_id)
  )
  WITH CHECK (
    app.current_business_role() IN ('super_admin', 'admin')
    OR app.is_board_moderator(board_id)
  );

CREATE POLICY review_entries_select_all ON app.review_entries
  FOR SELECT TO agent_kb_user
  USING (true);

CREATE POLICY review_entries_insert_own ON app.review_entries
  FOR INSERT TO agent_kb_user
  WITH CHECK (principal_id = app.current_principal_id());

CREATE POLICY review_entries_update_own ON app.review_entries
  FOR UPDATE TO agent_kb_user
  USING (principal_id = app.current_principal_id())
  WITH CHECK (principal_id = app.current_principal_id());

CREATE POLICY review_history_select_admin ON app.review_history
  FOR SELECT TO agent_kb_user
  USING (app.current_business_role() IN ('super_admin', 'admin'));

CREATE POLICY tags_select_all ON app.tags
  FOR SELECT TO agent_kb_user
  USING (true);

CREATE POLICY tags_insert_moderator_or_admin ON app.tags
  FOR INSERT TO agent_kb_user
  WITH CHECK (
    created_by = app.current_principal_id()
    AND (
      app.current_business_role() IN ('super_admin', 'admin')
      OR EXISTS (
        SELECT 1
        FROM app.board_moderators AS bm
        WHERE bm.principal_id = app.current_principal_id()
      )
    )
  );

CREATE POLICY post_tags_select_all ON app.post_tags
  FOR SELECT TO agent_kb_user
  USING (true);

CREATE POLICY post_tags_insert_author_or_admin ON app.post_tags
  FOR INSERT TO agent_kb_user
  WITH CHECK (
    EXISTS (
      SELECT 1
      FROM app.posts AS p
      WHERE p.id = post_id
        AND (
          p.author_id = app.current_principal_id()
          OR app.current_business_role() IN ('super_admin', 'admin')
        )
    )
  );

CREATE POLICY post_tags_delete_admin ON app.post_tags
  FOR DELETE TO agent_kb_user
  USING (app.current_business_role() IN ('super_admin', 'admin'));

INSERT INTO app.principals (principal_type, display_name, business_role, pg_login_role)
VALUES ('human', 'Local Postgres Bootstrap', 'super_admin', 'postgres')
ON CONFLICT (pg_login_role) DO NOTHING;

COMMIT;
