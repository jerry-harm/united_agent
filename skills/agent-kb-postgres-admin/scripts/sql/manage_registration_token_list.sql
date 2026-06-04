DO $$
BEGIN
  IF NOT auth.can_write() OR NOT auth.is_admin() THEN
    RAISE EXCEPTION 'policy violation: only active admin or super_admin may list registration tokens';
  END IF;
END
$$;

SELECT id, token, max_uses, uses_consumed, expires_at, revoked_at, last_used_at, created_at, created_by
FROM auth.registration_tokens
ORDER BY created_at DESC, id DESC;
