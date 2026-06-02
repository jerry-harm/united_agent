DO $$
BEGIN
  IF auth.is_admin()
     AND NOT auth.is_super_admin()
     AND {{global_role}} <> 'normal_user' THEN
    RAISE EXCEPTION 'policy violation: admin may create only normal_user accounts';
  ELSIF auth.is_super_admin()
     AND {{global_role}} NOT IN ('normal_user', 'admin') THEN
    RAISE EXCEPTION 'policy violation: super_admin may create only normal_user or admin accounts';
  ELSIF NOT auth.is_admin() THEN
    RAISE EXCEPTION 'policy violation: only admin or super_admin may create accounts';
  END IF;
END
$$;

WITH created_account AS (
  INSERT INTO auth.accounts (principal_type, display_name, pg_login_role, account_status)
  VALUES ({{principal_type}}, {{display_name}}, {{login_role}}, 'active')
  RETURNING id, principal_type, display_name, pg_login_role, account_status
),
created_login AS (
  SELECT auth.create_account_login(
    {{login_role}},
    {{new_password}}
  )
),
granted_role AS (
  INSERT INTO auth.principal_global_roles (account_id, role_name, granted_by)
  SELECT created_account.id, {{global_role}}, auth.current_account_id()
  FROM created_account
  ON CONFLICT (account_id, role_name) DO NOTHING
)
SELECT id, principal_type, display_name, pg_login_role, account_status
FROM created_account;
