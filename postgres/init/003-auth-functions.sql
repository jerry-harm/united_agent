-- 暴露 updated_at 的可变表共用的时间戳触发器。
CREATE FUNCTION auth.set_updated_at() RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
  NEW.updated_at := now();
  RETURN NEW;
END;
$$;

-- 把当前应用账号从已认证的 PostgreSQL 登录解析出来。
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

-- 解析当前账号状态，供写路径与策略判定使用。
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

-- 通用全局角色判定，给更细的 admin 检查用。
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

-- admin 同时覆盖 admin 与 super_admin 授予。
CREATE FUNCTION auth.is_admin() RETURNS boolean
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = auth, pg_catalog
AS $$
  SELECT auth.has_global_role('admin') OR auth.has_global_role('super_admin');
$$;

-- super_admin 独立保留：部分写路径比普通 admin 更严格。
CREATE FUNCTION auth.is_super_admin() RETURNS boolean
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = auth, pg_catalog
AS $$
  SELECT auth.has_global_role('super_admin');
$$;

CREATE FUNCTION auth.is_guest() RETURNS boolean
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = auth, pg_catalog
AS $$
  SELECT EXISTS (
    SELECT 1
    FROM auth.accounts AS a
    WHERE a.pg_login_role = session_user
      AND a.pg_login_role = 'guest'
  );
$$;

CREATE FUNCTION auth.account_has_global_role(target_account_id bigint, p_role_name auth.global_role) RETURNS boolean
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = auth, pg_catalog
AS $$
  SELECT EXISTS (
    SELECT 1
    FROM auth.principal_global_roles AS pgr
    WHERE pgr.account_id = target_account_id
      AND pgr.role_name = p_role_name
  );
$$;

-- 写能力集中闸门：调用方必须能解析到已知账号且状态仍为 active。
CREATE FUNCTION auth.can_write() RETURNS boolean
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = auth, pg_catalog
AS $$
  SELECT auth.current_account_id() IS NOT NULL
     AND auth.current_account_status() = 'active'::auth.account_status;
$$;

CREATE FUNCTION auth.can_manage_account(target_account_id bigint) RETURNS boolean
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = auth, pg_catalog
AS $$
  SELECT auth.can_write()
     AND EXISTS (
        SELECT 1
        FROM auth.accounts AS a
        WHERE a.id = target_account_id
          AND a.pg_login_role <> 'deleted_account_tombstone'
      )
     AND NOT auth.account_has_global_role(target_account_id, 'super_admin')
     AND (
       auth.is_super_admin()
       OR (
         auth.is_admin()
         AND NOT auth.account_has_global_role(target_account_id, 'admin')
       )
      );
$$;

CREATE FUNCTION auth.create_account_login_unchecked(
  p_pg_login_role text,
  p_pg_password text
) RETURNS text
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = auth, pg_catalog
AS $$
BEGIN
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

-- 特权 helper：创建 PostgreSQL 登录并挂到共享运行时角色上，供应用访问。
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

  RETURN auth.create_account_login_unchecked(p_pg_login_role, p_pg_password);
END;
$$;

CREATE FUNCTION auth.create_account_with_login(
  p_principal_type auth.principal_type,
  p_display_name text,
  p_login_role text,
  p_password text,
  p_global_role auth.global_role DEFAULT 'normal_user'
) RETURNS TABLE (
  account_id bigint,
  principal_type auth.principal_type,
  display_name text,
  pg_login_role text,
  account_status auth.account_status
)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = auth, app, pg_catalog
AS $$
DECLARE
  created_account_id bigint;
  created_pg_login_role text;
  created_account_status auth.account_status;
  created_principal_type auth.principal_type;
  created_display_name text;
BEGIN
  IF NOT auth.can_write() OR NOT auth.is_admin() THEN
    RAISE EXCEPTION 'policy violation: only admin or super_admin may create accounts';
  ELSIF auth.is_admin()
     AND NOT auth.is_super_admin()
     AND p_global_role <> 'normal_user' THEN
    RAISE EXCEPTION 'policy violation: admin may create only normal_user accounts';
  ELSIF auth.is_super_admin()
     AND p_global_role NOT IN ('normal_user', 'admin') THEN
    RAISE EXCEPTION 'policy violation: super_admin may create only normal_user or admin accounts';
  END IF;

  PERFORM auth.create_account_login(p_login_role, p_password);

  INSERT INTO auth.accounts (pg_login_role, account_status)
  VALUES (p_login_role, 'active')
  RETURNING auth.accounts.id, auth.accounts.pg_login_role, auth.accounts.account_status
  INTO created_account_id, created_pg_login_role, created_account_status;

  INSERT INTO app.profiles (account_id, principal_type, display_name)
  VALUES (created_account_id, p_principal_type, p_display_name)
  RETURNING app.profiles.principal_type, app.profiles.display_name
  INTO created_principal_type, created_display_name;

  INSERT INTO auth.principal_global_roles (account_id, role_name, granted_by)
  VALUES (created_account_id, p_global_role, auth.current_account_id())
  ON CONFLICT ON CONSTRAINT principal_global_roles_pkey DO NOTHING;

  RETURN QUERY
  SELECT created_account_id,
         created_principal_type,
         created_display_name,
         created_pg_login_role,
         created_account_status;
EXCEPTION
  WHEN others THEN
    IF to_regrole(p_login_role) IS NOT NULL THEN
      EXECUTE format('DROP ROLE %I', p_login_role);
    END IF;
    RAISE;
END;
$$;

CREATE FUNCTION auth.issue_registration_token(
  p_token text,
  p_max_uses integer,
  p_expires_at timestamptz DEFAULT NULL
) RETURNS TABLE (
  id bigint,
  token text,
  max_uses integer,
  uses_consumed integer,
  expires_at timestamptz,
  revoked_at timestamptz,
  created_at timestamptz,
  created_by bigint
)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = auth, pg_catalog
AS $$
BEGIN
  IF NOT auth.can_write() OR NOT auth.is_admin() THEN
    RAISE EXCEPTION 'only admin or super_admin may create registration tokens';
  END IF;

  IF coalesce(btrim(p_token), '') = '' THEN
    RAISE EXCEPTION 'registration token must not be empty';
  END IF;

  IF p_max_uses IS NULL OR p_max_uses <= 0 THEN
    RAISE EXCEPTION 'registration token max_uses must be greater than zero';
  END IF;

  RETURN QUERY
  INSERT INTO auth.registration_tokens (token, max_uses, expires_at, created_by)
  VALUES (p_token, p_max_uses, p_expires_at, auth.current_account_id())
  RETURNING
    auth.registration_tokens.id,
    auth.registration_tokens.token,
    auth.registration_tokens.max_uses,
    auth.registration_tokens.uses_consumed,
    auth.registration_tokens.expires_at,
    auth.registration_tokens.revoked_at,
    auth.registration_tokens.created_at,
    auth.registration_tokens.created_by;
END;
$$;

CREATE FUNCTION auth.register_with_token(
  p_token text,
  p_principal_type auth.principal_type,
  p_display_name text,
  p_login_role text,
  p_password text
) RETURNS TABLE (
  id bigint,
  principal_type auth.principal_type,
  display_name text,
  pg_login_role text,
  account_status auth.account_status,
  remaining_uses integer
)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = auth, app, pg_catalog
AS $$
DECLARE
  registration_token auth.registration_tokens%ROWTYPE;
  created_account_id bigint;
  created_pg_login_role text;
  created_account_status auth.account_status;
  created_principal_type auth.principal_type;
  created_display_name text;
  remaining integer;
BEGIN
  IF NOT auth.is_guest() THEN
    RAISE EXCEPTION 'registration via token is only allowed for the guest account';
  END IF;

  IF coalesce(btrim(p_token), '') = '' THEN
    RAISE EXCEPTION 'registration token must not be empty';
  END IF;

  SELECT * INTO registration_token
  FROM auth.registration_tokens
  WHERE token = p_token
  FOR UPDATE;

  IF registration_token.id IS NULL THEN
    RAISE EXCEPTION 'invalid registration token';
  END IF;

  IF registration_token.revoked_at IS NOT NULL THEN
    RAISE EXCEPTION 'registration token has been revoked';
  END IF;

  IF registration_token.expires_at IS NOT NULL AND registration_token.expires_at <= now() THEN
    RAISE EXCEPTION 'registration token has expired';
  END IF;

  IF registration_token.uses_consumed >= registration_token.max_uses THEN
    RAISE EXCEPTION 'registration token has no remaining uses';
  END IF;

  PERFORM auth.create_account_login_unchecked(p_login_role, p_password);

  INSERT INTO auth.accounts (pg_login_role, account_status)
  VALUES (p_login_role, 'active')
  RETURNING auth.accounts.id, auth.accounts.pg_login_role, auth.accounts.account_status INTO created_account_id, created_pg_login_role, created_account_status;

  INSERT INTO app.profiles (account_id, principal_type, display_name)
  VALUES (created_account_id, p_principal_type, p_display_name)
  RETURNING app.profiles.principal_type, app.profiles.display_name INTO created_principal_type, created_display_name;

  INSERT INTO auth.principal_global_roles (account_id, role_name, granted_by)
  VALUES (created_account_id, 'normal_user'::auth.global_role, registration_token.created_by)
  ON CONFLICT ON CONSTRAINT principal_global_roles_pkey DO NOTHING;

  UPDATE auth.registration_tokens
  SET uses_consumed = uses_consumed + 1,
      last_used_at = now()
  WHERE auth.registration_tokens.id = registration_token.id
    AND uses_consumed < max_uses
  RETURNING max_uses - uses_consumed INTO remaining;

  IF remaining IS NULL THEN
    RAISE EXCEPTION 'registration token has no remaining uses';
  END IF;

  RETURN QUERY
  SELECT created_account_id,
         created_principal_type,
         created_display_name,
         created_pg_login_role,
         created_account_status,
         remaining;
EXCEPTION
  WHEN others THEN
    IF to_regrole(p_login_role) IS NOT NULL THEN
      EXECUTE format('DROP ROLE %I', p_login_role);
    END IF;
    RAISE;
END;
$$;

CREATE FUNCTION auth.change_own_password(p_new_password text) RETURNS text
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = auth, pg_catalog
AS $$
DECLARE
  current_id bigint;
  current_login text;
BEGIN
  current_id := auth.current_account_id();
  IF current_id IS NULL THEN
    RAISE EXCEPTION 'login resolved to no auth.accounts row';
  END IF;

  IF NOT auth.can_write() THEN
    RAISE EXCEPTION 'only active accounts may change their own password';
  END IF;

  IF coalesce(btrim(p_new_password), '') = '' THEN
    RAISE EXCEPTION 'password must not be empty';
  END IF;

  SELECT a.pg_login_role INTO current_login
  FROM auth.accounts AS a
  WHERE a.id = current_id;

  EXECUTE format('ALTER ROLE %I PASSWORD %L', current_login, p_new_password);
  RETURN current_login;
END;
$$;

CREATE FUNCTION auth.reset_managed_account_password(
  p_target_account_id bigint,
  p_new_password text
) RETURNS text
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = auth, pg_catalog
AS $$
DECLARE
  target_id bigint;
  target_login text;
BEGIN
  SELECT a.id, a.pg_login_role INTO target_id, target_login
  FROM auth.accounts AS a
  WHERE a.id = p_target_account_id;

  IF target_id IS NULL THEN
    RAISE EXCEPTION 'account % does not exist', p_target_account_id;
  END IF;

  IF NOT auth.can_manage_account(target_id) THEN
    RAISE EXCEPTION 'policy violation: actor may only reset passwords for permitted accounts';
  END IF;

  IF coalesce(btrim(p_new_password), '') = '' THEN
    RAISE EXCEPTION 'password must not be empty';
  END IF;

  EXECUTE format('ALTER ROLE %I PASSWORD %L', target_login, p_new_password);
  RETURN target_login;
END;
$$;

CREATE FUNCTION auth.disable_managed_account(
  p_target_account_id bigint
) RETURNS TABLE (
  account_id bigint,
  pg_login_role text,
  account_status auth.account_status
)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = auth, pg_catalog
AS $$
DECLARE
  target_id bigint;
  target_login text;
  target_status auth.account_status;
  tombstone_id bigint;
BEGIN
  SELECT a.id, a.pg_login_role INTO target_id, target_login
  FROM auth.accounts AS a
  WHERE a.id = p_target_account_id;

  IF target_id IS NULL THEN
    RAISE EXCEPTION 'account % does not exist', p_target_account_id;
  END IF;

  IF NOT auth.can_manage_account(target_id) THEN
    RAISE EXCEPTION 'policy violation: actor may only disable permitted accounts';
  END IF;

  SELECT a.id INTO tombstone_id
  FROM auth.accounts AS a
  WHERE a.pg_login_role = 'deleted_account_tombstone';

  IF tombstone_id IS NOT NULL AND tombstone_id = target_id THEN
    RAISE EXCEPTION 'policy violation: cannot disable the shared deleted-account tombstone';
  END IF;

  UPDATE auth.accounts
  SET account_status = 'disabled'::auth.account_status
  WHERE id = target_id
  RETURNING auth.accounts.id, auth.accounts.pg_login_role, auth.accounts.account_status
  INTO target_id, target_login, target_status;

  RETURN QUERY
  SELECT target_id, target_login, target_status;
END;
$$;

CREATE FUNCTION auth.delete_managed_account(p_target_account_id bigint) RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = auth, app, pg_catalog
AS $$
DECLARE
  target_id bigint;
  target_login text;
  tombstone_id bigint;
  reassigned_posts bigint;
  reassigned_reviews bigint;
  reassigned_history bigint;
  posts_trigger_disabled boolean := false;
BEGIN
  SELECT a.id, a.pg_login_role INTO target_id, target_login
  FROM auth.accounts AS a
  WHERE a.id = p_target_account_id;

  IF target_id IS NULL THEN
    RAISE EXCEPTION 'account % does not exist', p_target_account_id;
  END IF;

  IF NOT auth.can_manage_account(target_id) THEN
    RAISE EXCEPTION 'policy violation: actor may only delete permitted accounts';
  END IF;

  SELECT a.id INTO tombstone_id
  FROM auth.accounts AS a
  WHERE a.pg_login_role = 'deleted_account_tombstone';

  IF tombstone_id IS NULL THEN
    RAISE EXCEPTION 'shared deleted-account tombstone is missing from auth.accounts';
  END IF;

  IF tombstone_id = target_id THEN
    RAISE EXCEPTION 'policy violation: cannot delete the shared deleted-account tombstone';
  END IF;

  ALTER TABLE app.posts DISABLE TRIGGER trg_posts_immutable;
  posts_trigger_disabled := true;

  UPDATE app.posts
  SET author_id = tombstone_id
  WHERE author_id = target_id;
  GET DIAGNOSTICS reassigned_posts = ROW_COUNT;

  ALTER TABLE app.posts ENABLE TRIGGER trg_posts_immutable;
  posts_trigger_disabled := false;

  UPDATE app.review_entries
  SET account_id = tombstone_id
  WHERE account_id = target_id;
  GET DIAGNOSTICS reassigned_reviews = ROW_COUNT;

  UPDATE app.review_history
  SET replaced_by = tombstone_id
  WHERE replaced_by = target_id;
  GET DIAGNOSTICS reassigned_history = ROW_COUNT;

  DELETE FROM auth.principal_global_roles WHERE account_id = target_id;
  DELETE FROM auth.accounts WHERE id = target_id;

  IF to_regrole(target_login) IS NOT NULL THEN
    EXECUTE format('DROP ROLE %I', target_login);
  END IF;

  RAISE NOTICE 'deleted account % (login %): reassigned % posts, % review entries, % review history rows to tombstone',
    target_id, target_login, reassigned_posts, reassigned_reviews, reassigned_history;
EXCEPTION
  WHEN others THEN
    IF posts_trigger_disabled THEN
      ALTER TABLE app.posts ENABLE TRIGGER trg_posts_immutable;
    END IF;
    RAISE;
END;
$$;

CREATE FUNCTION auth.grant_global_role(
  p_target_account_id bigint,
  p_role_name auth.global_role
) RETURNS TABLE (
  account_id bigint,
  role_name text,
  granted_at timestamptz,
  granted_by bigint
)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = auth, pg_catalog
AS $$
DECLARE
  target_id bigint;
BEGIN
  IF NOT auth.is_super_admin() OR NOT auth.can_write() THEN
    RAISE EXCEPTION 'policy violation: only active super_admin may grant global roles';
  END IF;

  SELECT a.id INTO target_id
  FROM auth.accounts AS a
  WHERE a.id = p_target_account_id;

  IF target_id IS NULL THEN
    RAISE EXCEPTION 'account % does not exist', p_target_account_id;
  END IF;

  IF p_role_name = 'super_admin'::auth.global_role THEN
    RAISE EXCEPTION 'policy violation: use direct database maintenance for super_admin role changes';
  END IF;

  INSERT INTO auth.principal_global_roles (account_id, role_name, granted_by)
  VALUES (target_id, p_role_name, auth.current_account_id())
  ON CONFLICT ON CONSTRAINT principal_global_roles_pkey DO NOTHING;

  RETURN QUERY
  SELECT pgr.account_id,
         pgr.role_name::text,
         pgr.granted_at,
         pgr.granted_by
  FROM auth.principal_global_roles AS pgr
  WHERE pgr.account_id = target_id
    AND pgr.role_name = p_role_name;
END;
$$;

CREATE FUNCTION auth.revoke_global_role(
  p_target_account_id bigint,
  p_role_name auth.global_role
) RETURNS TABLE (
  account_id bigint,
  role_name text,
  granted_at timestamptz,
  granted_by bigint
)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = auth, pg_catalog
AS $$
DECLARE
  target_id bigint;
BEGIN
  IF NOT auth.is_super_admin() OR NOT auth.can_write() THEN
    RAISE EXCEPTION 'policy violation: only active super_admin may revoke global roles';
  END IF;

  SELECT a.id INTO target_id
  FROM auth.accounts AS a
  WHERE a.id = p_target_account_id;

  IF target_id IS NULL THEN
    RAISE EXCEPTION 'account % does not exist', p_target_account_id;
  END IF;

  IF p_role_name = 'super_admin'::auth.global_role THEN
    RAISE EXCEPTION 'policy violation: use direct database maintenance for super_admin role changes';
  END IF;

  DELETE FROM auth.principal_global_roles
  WHERE account_id = target_id
    AND role_name = p_role_name;

  RETURN QUERY
  SELECT pgr.account_id,
         pgr.role_name::text,
         pgr.granted_at,
         pgr.granted_by
  FROM auth.principal_global_roles AS pgr
  WHERE pgr.account_id = target_id
  ORDER BY pgr.role_name;
END;
$$;
