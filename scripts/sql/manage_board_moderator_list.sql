DO $$
BEGIN
  IF app.current_business_role() NOT IN ('admin'::app.business_role, 'super_admin'::app.business_role) THEN
    RAISE EXCEPTION 'policy violation: only admin or super_admin may manage moderators';
  END IF;
END
$$;

SELECT board_id, principal_id, granted_at, granted_by
FROM app.board_moderators
ORDER BY board_id, principal_id;
