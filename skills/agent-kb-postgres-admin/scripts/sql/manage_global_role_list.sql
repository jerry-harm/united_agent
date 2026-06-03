DO $$
BEGIN
  IF NOT auth.is_admin() OR NOT auth.can_write() THEN
    RAISE EXCEPTION 'policy violation: only active admin or super_admin may list global roles';
  END IF;
END
$$;

SELECT account_id, role_name::text AS role_name, granted_at, granted_by
FROM auth.principal_global_roles
ORDER BY account_id, role_name;
