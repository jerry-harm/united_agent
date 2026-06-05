-- 身份与授权表都在 auth schema。
-- auth.accounts 只存内部身份字段（pg_login_role + account_status），公开资料字段（principal_type, display_name, bio）放在 app.profiles。
CREATE TABLE auth.accounts (
  id bigserial PRIMARY KEY,
  pg_login_role text NOT NULL UNIQUE CHECK (btrim(pg_login_role) <> ''),
  account_status auth.account_status NOT NULL DEFAULT 'active',
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE app.profiles (
  id bigserial PRIMARY KEY,
  account_id bigint NOT NULL UNIQUE REFERENCES auth.accounts(id) ON DELETE CASCADE,
  principal_type auth.principal_type NOT NULL,
  display_name text NOT NULL CHECK (btrim(display_name) <> ''),
  bio text NOT NULL DEFAULT '',
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

-- 全局角色授予拆出独立表，单账号可持有多个角色，避免压扁到账号行。
CREATE TABLE auth.principal_global_roles (
  account_id bigint NOT NULL REFERENCES auth.accounts(id) ON DELETE CASCADE,
  role_name auth.global_role NOT NULL,
  granted_at timestamptz NOT NULL DEFAULT now(),
  granted_by bigint REFERENCES auth.accounts(id) ON DELETE SET NULL,
  PRIMARY KEY (account_id, role_name)
);

CREATE TABLE auth.registration_tokens (
  id bigserial PRIMARY KEY,
  token text NOT NULL UNIQUE CHECK (btrim(token) <> ''),
  max_uses integer NOT NULL CHECK (max_uses > 0),
  uses_consumed integer NOT NULL DEFAULT 0 CHECK (uses_consumed >= 0 AND uses_consumed <= max_uses),
  expires_at timestamptz,
  revoked_at timestamptz,
  last_used_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now(),
  created_by bigint REFERENCES auth.accounts(id) ON DELETE SET NULL
);

-- 业务内容表都在 app schema。
CREATE TABLE app.categories (
  id bigserial PRIMARY KEY,
  slug text NOT NULL UNIQUE CHECK (btrim(slug) <> ''),
  title text NOT NULL CHECK (btrim(title) <> ''),
  description text NOT NULL DEFAULT '',
  category_type app.category_type NOT NULL DEFAULT 'discussion',
  created_at timestamptz NOT NULL DEFAULT now(),
  created_by bigint NOT NULL REFERENCES auth.accounts(id) ON DELETE RESTRICT
);

CREATE TABLE app.posts (
  id bigserial PRIMARY KEY,
  category_id bigint NOT NULL REFERENCES app.categories(id) ON DELETE RESTRICT,
  author_id bigint NOT NULL REFERENCES auth.accounts(id) ON DELETE RESTRICT,
  content_type text NOT NULL CHECK (btrim(content_type) <> ''),
  title text NOT NULL CHECK (btrim(title) <> ''),
  body text NOT NULL,
  verification app.verification_state NOT NULL DEFAULT 'progressing',
  improvement_of bigint REFERENCES app.posts(id) ON DELETE RESTRICT,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CHECK (improvement_of IS NULL OR improvement_of <> id)
);

CREATE TABLE app.review_entries (
  id bigserial PRIMARY KEY,
  post_id bigint NOT NULL REFERENCES app.posts(id) ON DELETE CASCADE,
  account_id bigint NOT NULL REFERENCES auth.accounts(id) ON DELETE RESTRICT,
  lgtm boolean NOT NULL DEFAULT false,
  conclusion text NOT NULL DEFAULT '',
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (post_id, account_id)
);

CREATE TABLE app.review_history (
  id bigserial PRIMARY KEY,
  review_entry_id bigint NOT NULL REFERENCES app.review_entries(id) ON DELETE CASCADE,
  replaced_at timestamptz NOT NULL DEFAULT now(),
  lgtm boolean NOT NULL,
  conclusion text NOT NULL,
  replaced_by bigint NOT NULL REFERENCES auth.accounts(id) ON DELETE RESTRICT
);

CREATE FUNCTION app.is_allowed_text_upload_mime(p_mime_type text) RETURNS boolean
LANGUAGE sql
IMMUTABLE
SET search_path = app, pg_catalog
AS $$
  SELECT lower(coalesce(btrim(p_mime_type), '')) = ANY (
    ARRAY[
      'text/plain',
      'text/markdown',
      'text/csv',
      'text/html',
      'text/xml',
      'text/yaml',
      'application/json',
      'application/xml',
      'application/yaml'
    ]
  );
$$;

CREATE TABLE app.file_blobs (
  id bigserial PRIMARY KEY,
  mime_type text NOT NULL CHECK (app.is_allowed_text_upload_mime(mime_type)),
  content_text text NOT NULL,
  content_sha256 text NOT NULL UNIQUE CHECK (btrim(content_sha256) <> ''),
  size_bytes integer GENERATED ALWAYS AS (octet_length(content_text)) STORED,
  created_at timestamptz NOT NULL DEFAULT now(),
  CHECK (size_bytes >= 0 AND size_bytes <= 10485760)
);

CREATE TABLE app.post_attachments (
  post_id bigint NOT NULL REFERENCES app.posts(id) ON DELETE CASCADE,
  file_blob_id bigint NOT NULL REFERENCES app.file_blobs(id) ON DELETE RESTRICT,
  position integer NOT NULL CHECK (position >= 0),
  created_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (post_id, file_blob_id),
  UNIQUE (post_id, position)
);

CREATE TABLE app.review_entry_attachments (
  review_entry_id bigint NOT NULL REFERENCES app.review_entries(id) ON DELETE CASCADE,
  file_blob_id bigint NOT NULL REFERENCES app.file_blobs(id) ON DELETE RESTRICT,
  position integer NOT NULL CHECK (position >= 0),
  created_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (review_entry_id, file_blob_id),
  UNIQUE (review_entry_id, position)
);

CREATE TABLE app.tags (
  id bigserial PRIMARY KEY,
  name text NOT NULL UNIQUE CHECK (btrim(name) <> ''),
  created_at timestamptz NOT NULL DEFAULT now(),
  created_by bigint NOT NULL REFERENCES auth.accounts(id) ON DELETE RESTRICT
);

CREATE TABLE app.post_tags (
  post_id bigint NOT NULL REFERENCES app.posts(id) ON DELETE CASCADE,
  tag_id bigint NOT NULL REFERENCES app.tags(id) ON DELETE CASCADE,
  PRIMARY KEY (post_id, tag_id)
);

-- 索引覆盖 RLS 与 category 查询中的外键 / 授权热点路径。
CREATE INDEX idx_principal_global_roles_role_name ON auth.principal_global_roles(role_name, account_id);
CREATE INDEX idx_registration_tokens_active_lookup ON auth.registration_tokens(token) WHERE revoked_at IS NULL;
CREATE INDEX idx_posts_category ON app.posts(category_id);
CREATE INDEX idx_posts_improvement ON app.posts(improvement_of) WHERE improvement_of IS NOT NULL;
CREATE INDEX idx_posts_verification ON app.posts(category_id, verification);
CREATE INDEX idx_review_history_entry ON app.review_history(review_entry_id);
CREATE INDEX idx_post_attachments_blob ON app.post_attachments(file_blob_id, post_id);
CREATE INDEX idx_review_attachments_blob ON app.review_entry_attachments(file_blob_id, review_entry_id);
CREATE INDEX idx_post_tags_tag ON app.post_tags(tag_id);
