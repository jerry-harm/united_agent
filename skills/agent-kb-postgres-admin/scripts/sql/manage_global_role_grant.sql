DO $$
DECLARE
  target_id bigint;
BEGIN
  IF NOT auth.is_super_admin() OR NOT auth.can_write() THEN
    RAISE EXCEPTION 'policy violation: only active super_admin may grant global roles';
  END IF;

  SELECT id INTO target_id FROM auth.accounts WHERE id = {{account_id}}::bigint;
  IF target_id IS NULL THEN
    RAISE EXCEPTION 'account % does not exist', {{account_id}};
  END IF;

  IF {{role_name}}::auth.global_role = 'super_admin'::auth.global_role THEN
    RAISE EXCEPTION 'policy violation: use direct database maintenance for super_admin role changes';
  END IF;

  INSERT INTO auth.principal_global_roles (account_id, role_name, granted_by)
  VALUES (target_id, {{role_name}}::auth.global_role, auth.current_account_id())
  ON CONFLICT (account_id, role_name) DO NOTHING;
END
$$;

SELECT pgr.account_id, pgr.role_name::text AS role_name, pgr.granted_at, pgr.granted_by
FROM auth.principal_global_roles AS pgr
WHERE pgr.account_id = {{account_id}}::bigint
  AND pgr.role_name = {{role_name}}::auth.global_role;
