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

CREATE FUNCTION app.file_upload_url(p_file_id bigint) RETURNS text
LANGUAGE sql
IMMUTABLE
SET search_path = app, pg_catalog
AS $$
  SELECT format('kb://uploaded-files/%s', p_file_id);
$$;

CREATE FUNCTION app.parse_uploaded_file_url(p_file_url text) RETURNS bigint
LANGUAGE sql
IMMUTABLE
SET search_path = app, pg_catalog
AS $$
  SELECT CASE
    WHEN p_file_url ~ '^kb://uploaded-files/[0-9]+$'
      THEN substring(p_file_url FROM '^kb://uploaded-files/([0-9]+)$')::bigint
    ELSE NULL
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
