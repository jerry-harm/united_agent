DO $$
DECLARE
  target_id bigint;
  tombstone_id bigint;
BEGIN
  IF NOT auth.is_admin() OR NOT auth.can_write() THEN
    RAISE EXCEPTION 'policy violation: only active admin or super_admin may disable accounts';
  END IF;

  SELECT id INTO target_id FROM auth.accounts WHERE id = {{account_id}}::bigint;
  IF target_id IS NULL THEN
    RAISE EXCEPTION 'account % does not exist', {{account_id}};
  END IF;

  SELECT id INTO tombstone_id
  FROM auth.accounts
  WHERE pg_login_role = 'deleted_account_tombstone';
  IF tombstone_id IS NOT NULL AND tombstone_id = target_id THEN
    RAISE EXCEPTION 'policy violation: cannot disable the shared deleted-account tombstone';
  END IF;

  UPDATE auth.accounts
  SET account_status = 'disabled'::auth.account_status
  WHERE id = target_id
  RETURNING id, pg_login_role, account_status::text;
END
$$;
