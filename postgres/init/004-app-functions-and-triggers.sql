-- 在 update 覆盖当前 review 行前先持久化旧 review 状态。
CREATE FUNCTION app.capture_review_history() RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = app, auth, pg_catalog
AS $$
BEGIN
  IF (OLD.conclusion IS DISTINCT FROM NEW.conclusion)
     OR (OLD.lgtm IS DISTINCT FROM NEW.lgtm) THEN
    INSERT INTO app.review_history (review_entry_id, replaced_at, lgtm, conclusion, replaced_by)
    VALUES (OLD.id, now(), OLD.lgtm, OLD.conclusion, auth.current_account_id());
  END IF;

  NEW.updated_at := now();
  RETURN NEW;
END;
$$;

-- Post 发布后即只读，仅 verification 可在后续流程中调整。
CREATE FUNCTION app.enforce_post_immutability() RETURNS trigger
LANGUAGE plpgsql
SET search_path = app, auth, pg_catalog
AS $$
BEGIN
  IF ROW(NEW.category_id, NEW.author_id, NEW.content_type, NEW.title, NEW.body, NEW.improvement_of, NEW.created_at)
     IS DISTINCT FROM
     ROW(OLD.category_id, OLD.author_id, OLD.content_type, OLD.title, OLD.body, OLD.improvement_of, OLD.created_at) THEN
    RAISE EXCEPTION 'posts are immutable after publication; only verification may change';
  END IF;

  NEW.updated_at := now();
  RETURN NEW;
END;
$$;

CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE FUNCTION app.ensure_file_blob(
  p_mime_type text,
  p_content_text text
) RETURNS bigint
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = app, auth, public, pg_catalog
AS $$
DECLARE
  v_file_blob_id bigint;
  v_content_sha256 text;
BEGIN
  IF NOT auth.can_write() THEN
    RAISE EXCEPTION 'only active accounts may create file blobs';
  END IF;

  IF NOT app.is_allowed_text_upload_mime(p_mime_type) THEN
    RAISE EXCEPTION 'mime type is not allowed: %', p_mime_type;
  END IF;

  v_content_sha256 = encode(digest(p_content_text, 'sha256'), 'hex');

  INSERT INTO app.file_blobs (mime_type, content_text, content_sha256)
  VALUES (
    p_mime_type,
    p_content_text,
    v_content_sha256
  )
  ON CONFLICT ON CONSTRAINT file_blobs_content_sha256_key DO UPDATE
  SET mime_type = app.file_blobs.mime_type
  RETURNING id INTO v_file_blob_id;

  RETURN v_file_blob_id;
END;
$$;

CREATE FUNCTION app.create_post(
  p_category_id bigint,
  p_content_type text,
  p_title text,
  p_body text,
  p_improvement_of bigint DEFAULT NULL
) RETURNS bigint
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = app, auth, pg_catalog
AS $$
DECLARE
  v_author_id bigint;
  v_post_id bigint;
  v_is_announcement_category boolean;
BEGIN
  IF NOT auth.can_write() THEN
    RAISE EXCEPTION 'only active accounts may create posts';
  END IF;

  v_author_id := auth.current_account_id();
  IF v_author_id IS NULL THEN
    RAISE EXCEPTION 'login resolved to no auth.accounts row';
  END IF;

  SELECT EXISTS (
    SELECT 1
    FROM app.categories AS c
    WHERE c.id = p_category_id
      AND c.slug = 'announcement'
  )
  INTO v_is_announcement_category;

  IF v_is_announcement_category AND NOT auth.is_admin() THEN
    RAISE EXCEPTION 'row-level security policy violation on table "posts"';
  END IF;

  INSERT INTO app.posts (category_id, author_id, content_type, title, body, improvement_of)
  VALUES (p_category_id, v_author_id, p_content_type, p_title, p_body, p_improvement_of)
  RETURNING id INTO v_post_id;

  RETURN v_post_id;
END;
$$;

CREATE FUNCTION app.create_post_with_attachments(
  p_category_id bigint,
  p_content_type text,
  p_title text,
  p_body text,
  p_improvement_of bigint DEFAULT NULL,
  p_attachments jsonb DEFAULT '[]'::jsonb
) RETURNS bigint
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = app, auth, pg_catalog
AS $$
DECLARE
  v_post_id bigint;
  v_attachment jsonb;
  v_ordinality bigint;
  v_file_blob_id bigint;
BEGIN
  v_post_id := app.create_post(
    p_category_id,
    p_content_type,
    p_title,
    p_body,
    p_improvement_of
  );

  FOR v_attachment, v_ordinality IN
    SELECT items.attachment, items.ordinality
    FROM jsonb_array_elements(coalesce(p_attachments, '[]'::jsonb)) WITH ORDINALITY AS items(attachment, ordinality)
  LOOP
    -- attachment kind contract: WHEN 'new' THEN create blob; WHEN 'existing' THEN reuse file_blob_id.
    IF v_attachment->>'kind' NOT IN ('new', 'existing') THEN
      RAISE EXCEPTION 'attachment kind must be new or existing';
    END IF;

    IF v_attachment->>'kind' = 'new' THEN
      v_file_blob_id := app.ensure_file_blob(
        v_attachment->>'mime_type',
        v_attachment->>'content_text'
      );
    ELSE
      v_file_blob_id := (v_attachment->>'file_blob_id')::bigint;
    END IF;

    IF v_file_blob_id IS NULL THEN
      RAISE EXCEPTION 'attachment must resolve to a file_blob_id';
    END IF;

    PERFORM 1 FROM app.file_blobs WHERE id = v_file_blob_id;
    IF NOT FOUND THEN
      RAISE EXCEPTION 'file blob % does not exist', v_file_blob_id;
    END IF;

    INSERT INTO app.post_attachments (post_id, file_blob_id, position)
    VALUES (v_post_id, v_file_blob_id, v_ordinality - 1);
  END LOOP;

  RETURN v_post_id;
END;
$$;

CREATE FUNCTION app.create_review_entry(
  p_post_id bigint,
  p_lgtm boolean DEFAULT false,
  p_conclusion text DEFAULT ''
) RETURNS bigint
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = app, auth, pg_catalog
AS $$
DECLARE
  v_account_id bigint;
  v_review_entry_id bigint;
BEGIN
  IF NOT auth.can_write() THEN
    RAISE EXCEPTION 'only active accounts may create review entries';
  END IF;

  v_account_id := auth.current_account_id();
  IF v_account_id IS NULL THEN
    RAISE EXCEPTION 'login resolved to no auth.accounts row';
  END IF;

  INSERT INTO app.review_entries (post_id, account_id, lgtm, conclusion)
  VALUES (p_post_id, v_account_id, coalesce(p_lgtm, false), coalesce(p_conclusion, ''))
  ON CONFLICT (post_id, account_id) DO UPDATE
  SET lgtm = EXCLUDED.lgtm,
      conclusion = EXCLUDED.conclusion,
      updated_at = now()
  RETURNING id INTO v_review_entry_id;

  RETURN v_review_entry_id;
END;
$$;

CREATE FUNCTION app.create_review_entry_with_attachments(
  p_post_id bigint,
  p_lgtm boolean DEFAULT false,
  p_conclusion text DEFAULT '',
  p_attachments jsonb DEFAULT '[]'::jsonb
) RETURNS bigint
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = app, auth, pg_catalog
AS $$
DECLARE
  v_review_entry_id bigint;
  v_attachment jsonb;
  v_ordinality bigint;
  v_file_blob_id bigint;
BEGIN
  v_review_entry_id := app.create_review_entry(p_post_id, p_lgtm, p_conclusion);

  DELETE FROM app.review_entry_attachments
  WHERE review_entry_id = v_review_entry_id;

  FOR v_attachment, v_ordinality IN
    SELECT items.attachment, items.ordinality
    FROM jsonb_array_elements(coalesce(p_attachments, '[]'::jsonb)) WITH ORDINALITY AS items(attachment, ordinality)
  LOOP
    -- attachment kind contract: WHEN 'new' THEN create blob; WHEN 'existing' THEN reuse file_blob_id.
    IF v_attachment->>'kind' NOT IN ('new', 'existing') THEN
      RAISE EXCEPTION 'attachment kind must be new or existing';
    END IF;

    IF v_attachment->>'kind' = 'new' THEN
      v_file_blob_id := app.ensure_file_blob(
        v_attachment->>'mime_type',
        v_attachment->>'content_text'
      );
    ELSE
      v_file_blob_id := (v_attachment->>'file_blob_id')::bigint;
    END IF;

    IF v_file_blob_id IS NULL THEN
      RAISE EXCEPTION 'attachment must resolve to a file_blob_id';
    END IF;

    PERFORM 1 FROM app.file_blobs WHERE id = v_file_blob_id;
    IF NOT FOUND THEN
      RAISE EXCEPTION 'file blob % does not exist', v_file_blob_id;
    END IF;

    INSERT INTO app.review_entry_attachments (review_entry_id, file_blob_id, position)
    VALUES (v_review_entry_id, v_file_blob_id, v_ordinality - 1);
  END LOOP;

  RETURN v_review_entry_id;
END;
$$;

-- 触发器统一维护 updated_at，并落实 review / post 的不变量。
CREATE TRIGGER trg_accounts_updated_at
BEFORE UPDATE ON auth.accounts
FOR EACH ROW
EXECUTE FUNCTION auth.set_updated_at();

CREATE TRIGGER trg_profiles_updated_at
BEFORE UPDATE ON app.profiles
FOR EACH ROW
EXECUTE FUNCTION auth.set_updated_at();

CREATE TRIGGER trg_review_entries_updated_at
BEFORE UPDATE ON app.review_entries
FOR EACH ROW
EXECUTE FUNCTION auth.set_updated_at();

CREATE TRIGGER trg_posts_updated_at
BEFORE UPDATE ON app.posts
FOR EACH ROW
EXECUTE FUNCTION auth.set_updated_at();

CREATE TRIGGER trg_review_history
BEFORE UPDATE ON app.review_entries
FOR EACH ROW
EXECUTE FUNCTION app.capture_review_history();

CREATE TRIGGER trg_posts_immutable
BEFORE UPDATE ON app.posts
FOR EACH ROW
EXECUTE FUNCTION app.enforce_post_immutability();

CREATE VIEW app.post_lgtm_rankings AS
SELECT
  rankings.post_id,
  rankings.category_id,
  rankings.category_slug,
  rankings.author_id,
  rankings.content_type,
  rankings.title,
  rankings.verification,
  rankings.created_at,
  rankings.review_count,
  rankings.lgtm_count,
  dense_rank() OVER (
    ORDER BY rankings.lgtm_count DESC, rankings.review_count DESC, rankings.created_at ASC, rankings.post_id ASC
  ) AS lgtm_rank
FROM (
  SELECT
    p.id AS post_id,
    p.category_id,
    c.slug AS category_slug,
    p.author_id,
    p.content_type,
    p.title,
    p.verification,
    p.created_at,
    count(re.id) AS review_count,
    count(*) FILTER (WHERE re.lgtm) AS lgtm_count
  FROM app.posts AS p
  JOIN app.categories AS c ON c.id = p.category_id
  LEFT JOIN app.review_entries AS re ON re.post_id = p.id
  GROUP BY
    p.id,
    p.category_id,
    c.slug,
    p.author_id,
    p.content_type,
    p.title,
    p.verification,
    p.created_at
) AS rankings;
