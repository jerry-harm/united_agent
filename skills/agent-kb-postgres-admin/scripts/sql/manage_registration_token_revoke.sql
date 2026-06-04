DO $$
BEGIN
  IF NOT auth.can_write() OR NOT auth.is_admin() THEN
    RAISE EXCEPTION 'policy violation: only active admin or super_admin may revoke registration tokens';
  END IF;
END
$$;

UPDATE auth.registration_tokens
SET revoked_at = now()
WHERE id = {{token_id}}::bigint
RETURNING id, token, max_uses, uses_consumed, expires_at, revoked_at, last_used_at, created_at, created_by;
