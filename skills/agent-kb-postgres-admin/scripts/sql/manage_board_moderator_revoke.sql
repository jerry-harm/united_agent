DO $$
BEGIN
  IF NOT auth.can_write() OR NOT auth.is_admin() THEN
    RAISE EXCEPTION 'policy violation: only admin or super_admin may manage moderators';
  END IF;
END
$$;

DELETE FROM auth.board_moderators
WHERE board_id = {{board_id}}::bigint
  AND account_id = {{account_id}}::bigint;
