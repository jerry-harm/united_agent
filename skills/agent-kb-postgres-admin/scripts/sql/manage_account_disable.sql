DO $$
DECLARE
  target_id bigint;
  tombstone_id bigint;
BEGIN
  SELECT id INTO target_id FROM auth.accounts WHERE id = {{account_id}}::bigint;
  IF target_id IS NULL THEN
    RAISE EXCEPTION 'account % does not exist', {{account_id}};
  END IF;

  IF NOT auth.can_manage_account(target_id) THEN
    RAISE EXCEPTION 'policy violation: actor may only disable permitted accounts';
  END IF;

  SELECT id INTO tombstone_id
  FROM auth.accounts
  WHERE pg_login_role = 'deleted_account_tombstone';
  IF tombstone_id IS NOT NULL AND tombstone_id = target_id THEN
    RAISE EXCEPTION 'policy violation: cannot disable the shared deleted-account tombstone';
  END IF;

  UPDATE auth.accounts
  SET account_status = 'disabled'::auth.account_status
  WHERE id = target_id;
END
$$;
