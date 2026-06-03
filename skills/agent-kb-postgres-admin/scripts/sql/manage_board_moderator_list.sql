DO $$
BEGIN
  IF NOT auth.is_admin() THEN
    RAISE EXCEPTION 'policy violation: only admin or super_admin may manage moderators';
  END IF;
END
$$;

SELECT board_id, account_id, granted_at, granted_by
FROM auth.board_moderators
ORDER BY board_id, account_id;
