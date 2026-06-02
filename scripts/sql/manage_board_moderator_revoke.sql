DO $$
BEGIN
  IF app.current_business_role() NOT IN ('admin'::app.business_role, 'super_admin'::app.business_role) THEN
    RAISE EXCEPTION 'policy violation: only admin or super_admin may manage moderators';
  END IF;
END
$$;

DELETE FROM app.board_moderators
WHERE board_id = {{board_id}}::bigint
  AND principal_id = {{principal_id}}::bigint;
