DO $$
DECLARE
  target_id bigint;
BEGIN
  IF NOT auth.is_super_admin() OR NOT auth.can_write() THEN
    RAISE EXCEPTION 'policy violation: only active super_admin may revoke global roles';
  END IF;

  SELECT id INTO target_id FROM auth.accounts WHERE id = {{account_id}}::bigint;
  IF target_id IS NULL THEN
    RAISE EXCEPTION 'account % does not exist', {{account_id}};
  END IF;

  DELETE FROM auth.principal_global_roles
  WHERE account_id = {{account_id}}::bigint
    AND role_name = {{role_name}}::auth.global_role;
END
$$;

SELECT pgr.account_id, pgr.role_name::text AS role_name, pgr.granted_at, pgr.granted_by
FROM auth.principal_global_roles AS pgr
WHERE pgr.account_id = {{account_id}}::bigint
ORDER BY pgr.role_name;
