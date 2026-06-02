DO $$
BEGIN
  IF NOT auth.is_admin() THEN
    RAISE EXCEPTION 'policy violation: only admin or super_admin may manage moderators';
  END IF;

  IF NOT EXISTS (
    SELECT 1
    FROM auth.accounts AS a
    WHERE a.id = {{account_id}}::bigint
      AND EXISTS (
        SELECT 1
        FROM auth.principal_global_roles AS pgr
        WHERE pgr.account_id = a.id
          AND pgr.role_name = 'normal_user'
      )
  ) THEN
    RAISE EXCEPTION 'policy violation: board moderators must be existing normal_user accounts';
  END IF;

  INSERT INTO auth.board_moderators (board_id, account_id, granted_by)
  VALUES ({{board_id}}::bigint, {{account_id}}::bigint, auth.current_account_id())
  ON CONFLICT (board_id, account_id) DO NOTHING;
END
$$;
