DO $$
DECLARE
  target_id bigint;
  target_login text;
  tombstone_id bigint;
  reassigned_posts bigint;
  reassigned_reviews bigint;
  reassigned_history bigint;
BEGIN
  IF NOT auth.is_super_admin() OR NOT auth.can_write() THEN
    RAISE EXCEPTION 'policy violation: only active super_admin may delete accounts';
  END IF;

  SELECT id, pg_login_role INTO target_id, target_login
  FROM auth.accounts
  WHERE id = {{account_id}}::bigint;

  IF target_id IS NULL THEN
    RAISE EXCEPTION 'account % does not exist', {{account_id}};
  END IF;

  SELECT id INTO tombstone_id
  FROM auth.accounts
  WHERE pg_login_role = 'deleted_account_tombstone';
  IF tombstone_id IS NULL THEN
    RAISE EXCEPTION 'shared deleted-account tombstone is missing from auth.accounts';
  END IF;
  IF tombstone_id = target_id THEN
    RAISE EXCEPTION 'policy violation: cannot delete the shared deleted-account tombstone';
  END IF;

  UPDATE app.posts
  SET author_id = tombstone_id
  WHERE author_id = target_id;
  GET DIAGNOSTICS reassigned_posts = ROW_COUNT;

  UPDATE app.review_entries
  SET account_id = tombstone_id
  WHERE account_id = target_id;
  GET DIAGNOSTICS reassigned_reviews = ROW_COUNT;

  UPDATE app.review_history
  SET replaced_by = tombstone_id
  WHERE replaced_by = target_id;
  GET DIAGNOSTICS reassigned_history = ROW_COUNT;

  DELETE FROM auth.principal_global_roles WHERE account_id = target_id;
  DELETE FROM auth.board_moderators WHERE account_id = target_id;
  DELETE FROM auth.accounts WHERE id = target_id;

  IF to_regrole(target_login) IS NOT NULL THEN
    EXECUTE format('DROP ROLE %I', target_login);
  END IF;

  RAISE NOTICE 'deleted account % (login %): reassigned % posts, % review entries, % review history rows to tombstone',
    target_id, target_login, reassigned_posts, reassigned_reviews, reassigned_history;
END
$$;
