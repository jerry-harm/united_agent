DO $$
BEGIN
  IF app.current_business_role() NOT IN ('admin'::app.business_role, 'super_admin'::app.business_role) THEN
    RAISE EXCEPTION 'policy violation: only admin or super_admin may manage moderators';
  END IF;

  IF NOT EXISTS (
    SELECT 1
    FROM app.principals
    WHERE id = {{principal_id}}::bigint
      AND business_role = 'normal_user'
  ) THEN
    RAISE EXCEPTION 'policy violation: board moderators must be existing normal_user principals';
  END IF;

  INSERT INTO app.board_moderators (board_id, principal_id, granted_by)
  VALUES ({{board_id}}::bigint, {{principal_id}}::bigint, app.current_principal_id())
  ON CONFLICT (board_id, principal_id) DO NOTHING;
END
$$;
