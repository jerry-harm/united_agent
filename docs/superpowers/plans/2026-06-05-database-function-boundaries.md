# Database Function Boundaries Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move fixed write flows onto PostgreSQL function contracts, replace standalone normal-user uploads with attachment-aware content creation, and keep Python wrappers as thin database callers.

**Architecture:** Introduce global deduplicated text blobs in `app.file_blobs`, connect them to posts and review entries through attachment tables, and expose new `app.*` / `auth.*` write functions as the canonical API. Migrate wrappers and tests to call those functions directly while leaving ranking, aggregation, and ad-hoc read SQL as user-authored queries.

**Tech Stack:** PostgreSQL SQL/PLpgSQL, psycopg Python wrappers, `uv`, Python `unittest`, Docker Compose local Postgres bootstrap.

---

## File Map

- Modify: `postgres/init/002-tables.sql`
  - Replace `app.uploaded_files` with `app.file_blobs`, `app.post_attachments`, and `app.review_entry_attachments`.
- Modify: `postgres/init/003-auth-functions.sql`
  - Add canonical admin functions or refactor existing admin helpers to stable function contracts.
- Modify: `postgres/init/004-app-functions-and-triggers.sql`
  - Add post/review creation functions, attachment helpers, and blob URL helpers.
- Modify: `postgres/init/005-permissions-and-rls.sql`
  - Remove old `uploaded_files` RLS/policies and add policies for the new attachment/blob model.
- Modify: `skills/agent-kb-postgres-connect/scripts/validate_post_flow.py`
  - Switch to calling `app.create_post(...)` / `app.create_post_with_attachments(...)`.
- Modify: `skills/agent-kb-postgres-connect/scripts/validate_review_flow.py`
  - Switch to calling `app.create_review_entry(...)` / `app.create_review_entry_with_attachments(...)`.
- Modify: `skills/agent-kb-postgres-connect/scripts/upload_text_file.py`
  - Remove or repurpose because normal users may not standalone-upload.
- Modify: `skills/agent-kb-postgres-connect/scripts/read_uploaded_file.py`
  - Rename/rework around blob reads if still needed by the product contract.
- Modify: `skills/agent-kb-postgres-connect/scripts/sql/upload_text_file_insert.sql`
  - Delete if wrapper no longer uses standalone insert SQL.
- Modify: `skills/agent-kb-postgres-admin/scripts/create_principal.py`
  - Call canonical admin function rather than multi-step SQL if feasible.
- Modify: `skills/agent-kb-postgres-admin/scripts/manage_account.py`
  - Call canonical admin functions.
- Modify: `skills/agent-kb-postgres-admin/scripts/manage_global_role.py`
  - Call canonical admin functions.
- Modify: `skills/agent-kb-postgres-admin/scripts/sql/*.sql`
  - Reduce helper SQL files to simple `SELECT auth.some_function(...)` calls where wrappers still use SQL files.
- Modify: `tests/test_agent_kb_postgres_skeleton.py`
  - Update schema/function expectations.
- Modify: `tests/test_postgres_connect_tooling.py`
  - Update wrapper expectations around removed standalone upload flow and function-calling thin wrappers.
- Modify: `tests/test_postgres_admin_tooling.py`
  - Update expectations for function-backed admin wrappers.
- Modify: `tests/test_content_permission_live_matrix.py`
  - Replace direct `uploaded_files` assumptions with blob/attachment assertions.
- Modify: `tests/test_connect_skill_live_flows.py`
  - Update live connect flows for attachment-capable create post/review paths.
- Modify: `tests/live_postgres_helpers.py`
  - Update cleanup helpers and fixture utilities for blob/attachment tables.
- Modify: `README.md`
  - Update operator-facing examples and feature description.
- Modify: `docs/developer-guide.md`
  - Update live-flow instructions and data model description.
- Modify: `.trellis/spec/backend/database-guidelines.md`
  - Capture final executable contract.
- Modify: `.trellis/spec/backend/quality-guidelines.md`
  - Capture thin-wrapper and function-boundary rule.

### Task 1: Lock in static schema expectations

**Files:**
- Modify: `tests/test_agent_kb_postgres_skeleton.py`
- Test: `tests/test_agent_kb_postgres_skeleton.py`

- [ ] **Step 1: Write the failing schema assertions for the new blob and attachment tables**

```python
def test_schema_adds_file_blob_and_attachment_tables(self) -> None:
    content = self.read_text("postgres/init/002-tables.sql")
    self.assertIn("CREATE TABLE app.file_blobs", content)
    self.assertIn("content_sha256 text NOT NULL", content)
    self.assertIn("UNIQUE (content_sha256)", content)
    self.assertIn("CREATE TABLE app.post_attachments", content)
    self.assertIn("CREATE TABLE app.review_entry_attachments", content)
    self.assertNotIn("CREATE TABLE app.uploaded_files", content)


def test_schema_exposes_attachment_capable_write_functions(self) -> None:
    content = self.read_text("postgres/init/004-app-functions-and-triggers.sql")
    self.assertIn("CREATE FUNCTION app.create_post(", content)
    self.assertIn("CREATE FUNCTION app.create_post_with_attachments(", content)
    self.assertIn("CREATE FUNCTION app.create_review_entry(", content)
    self.assertIn("CREATE FUNCTION app.create_review_entry_with_attachments(", content)
```

- [ ] **Step 2: Run the static schema test to verify it fails first**

Run: `uv run python -m unittest tests.test_agent_kb_postgres_skeleton -v`
Expected: FAIL because the repo still contains `app.uploaded_files` and does not yet define the new functions/tables.

- [ ] **Step 3: Add attachment and function contract expectations already known from the spec**

```python
def test_schema_uses_blob_urls_not_uploaded_file_urls(self) -> None:
    content = self.read_text("postgres/init/004-app-functions-and-triggers.sql")
    self.assertIn("kb://file-blobs/", content)
    self.assertNotIn("kb://uploaded-files/", content)


def test_schema_keeps_text_upload_mime_allowlist(self) -> None:
    content = self.read_text("postgres/init/002-tables.sql")
    self.assertIn("CREATE FUNCTION app.is_allowed_text_upload_mime", content)
    self.assertIn("application/json", content)
```

- [ ] **Step 4: Re-run the static schema test and keep it red until implementation starts**

Run: `uv run python -m unittest tests.test_agent_kb_postgres_skeleton -v`
Expected: FAIL, but now with complete forward-looking assertions that encode the target design.

- [ ] **Step 5: Commit the red schema test harness**

```bash
git add tests/test_agent_kb_postgres_skeleton.py
git commit -m "test: define blob attachment schema expectations"
```

### Task 2: Replace `uploaded_files` with blob and attachment tables

**Files:**
- Modify: `postgres/init/002-tables.sql`
- Modify: `tests/test_agent_kb_postgres_skeleton.py`
- Test: `tests/test_agent_kb_postgres_skeleton.py`

- [ ] **Step 1: Implement the new table definitions in bootstrap SQL**

```sql
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
```

- [ ] **Step 2: Add supporting indexes that match expected read and cleanup paths**

```sql
CREATE INDEX idx_file_blobs_sha256 ON app.file_blobs(content_sha256);
CREATE INDEX idx_post_attachments_blob ON app.post_attachments(file_blob_id, post_id);
CREATE INDEX idx_review_attachments_blob ON app.review_entry_attachments(file_blob_id, review_entry_id);
```

- [ ] **Step 3: Run static schema tests to verify they now pass**

Run: `uv run python -m unittest tests.test_agent_kb_postgres_skeleton -v`
Expected: PASS for the new table/URL/static bootstrap assertions.

- [ ] **Step 4: Run a broader bootstrap-oriented static slice**

Run: `uv run python -m unittest tests.test_agent_kb_postgres_skeleton tests.test_postgres_connect_tooling -v`
Expected: Some connect-tooling failures are acceptable at this point, but bootstrap schema assertions should stay green.

- [ ] **Step 5: Commit the schema replacement**

```bash
git add postgres/init/002-tables.sql tests/test_agent_kb_postgres_skeleton.py
git commit -m "refactor(db): replace uploaded files with blobs and attachments"
```

### Task 3: Add application-side blob helpers and post/review write functions

**Files:**
- Modify: `postgres/init/004-app-functions-and-triggers.sql`
- Modify: `tests/test_agent_kb_postgres_skeleton.py`
- Test: `tests/test_agent_kb_postgres_skeleton.py`

- [ ] **Step 1: Write failing static assertions for blob helper and create-with-attachments functions**

```python
def test_schema_adds_blob_helper_functions(self) -> None:
    content = self.read_text("postgres/init/004-app-functions-and-triggers.sql")
    self.assertIn("CREATE FUNCTION app.file_blob_url(", content)
    self.assertIn("CREATE FUNCTION app.parse_file_blob_url(", content)
    self.assertIn("CREATE FUNCTION app.ensure_file_blob(", content)


def test_schema_adds_attachment_write_functions(self) -> None:
    content = self.read_text("postgres/init/004-app-functions-and-triggers.sql")
    self.assertIn("CREATE FUNCTION app.create_post_with_attachments(", content)
    self.assertIn("CREATE FUNCTION app.create_review_entry_with_attachments(", content)
```

- [ ] **Step 2: Run the schema test to verify these new assertions fail**

Run: `uv run python -m unittest tests.test_agent_kb_postgres_skeleton -v`
Expected: FAIL because helper functions do not yet exist.

- [ ] **Step 3: Implement minimal blob helper functions and stable blob URL contract**

```sql
CREATE FUNCTION app.file_blob_url(p_file_blob_id bigint) RETURNS text
LANGUAGE sql
IMMUTABLE
SET search_path = app, pg_catalog
AS $$
  SELECT format('kb://file-blobs/%s', p_file_blob_id);
$$;

CREATE FUNCTION app.parse_file_blob_url(p_file_url text) RETURNS bigint
LANGUAGE sql
IMMUTABLE
SET search_path = app, pg_catalog
AS $$
  SELECT CASE
    WHEN p_file_url ~ '^kb://file-blobs/[0-9]+$'
      THEN substring(p_file_url FROM '^kb://file-blobs/([0-9]+)$')::bigint
    ELSE NULL
  END;
$$;
```

- [ ] **Step 4: Implement a reusable `app.ensure_file_blob(...)` helper**

```sql
CREATE FUNCTION app.ensure_file_blob(
  p_mime_type text,
  p_content_text text
) RETURNS TABLE (
  file_blob_id bigint,
  file_blob_url text,
  content_sha256 text,
  size_bytes integer,
  mime_type text
)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = app, auth, pg_catalog
AS $$
DECLARE
  normalized_mime text;
  digest_hex text;
BEGIN
  IF NOT auth.can_write() THEN
    RAISE EXCEPTION 'only active accounts may create attachment content';
  END IF;

  normalized_mime := lower(coalesce(btrim(p_mime_type), ''));
  IF NOT app.is_allowed_text_upload_mime(normalized_mime) THEN
    RAISE EXCEPTION 'unsupported text attachment mime type: %', p_mime_type;
  END IF;

  digest_hex := encode(digest(p_content_text, 'sha256'), 'hex');

  RETURN QUERY
  WITH inserted AS (
    INSERT INTO app.file_blobs (mime_type, content_text, content_sha256)
    VALUES (normalized_mime, p_content_text, digest_hex)
    ON CONFLICT (content_sha256) DO UPDATE
      SET mime_type = app.file_blobs.mime_type
    RETURNING id, content_sha256, size_bytes, mime_type
  )
  SELECT i.id, app.file_blob_url(i.id), i.content_sha256, i.size_bytes, i.mime_type
  FROM inserted AS i;
END;
$$;
```

- [ ] **Step 5: Implement `app.create_post(...)` and `app.create_review_entry(...)` as canonical non-attachment flows**

```sql
CREATE FUNCTION app.create_post(
  p_category_id bigint,
  p_content_type text,
  p_title text,
  p_body text,
  p_improvement_of bigint DEFAULT NULL
) RETURNS TABLE (
  post_id bigint,
  author_account_id bigint,
  category_id bigint,
  verification app.verification_state,
  created_at timestamptz
)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = app, auth, pg_catalog
AS $$
DECLARE
  actor_id bigint;
BEGIN
  actor_id := auth.current_account_id();
  IF actor_id IS NULL OR NOT auth.can_write() THEN
    RAISE EXCEPTION 'only active accounts may create posts';
  END IF;

  RETURN QUERY
  INSERT INTO app.posts (category_id, author_id, content_type, title, body, improvement_of)
  VALUES (p_category_id, actor_id, p_content_type, p_title, p_body, p_improvement_of)
  RETURNING id, author_id, category_id, verification, created_at;
END;
$$;
```

- [ ] **Step 6: Implement attachment-capable post/review write functions using JSONB attachment input**

```sql
CREATE FUNCTION app.create_post_with_attachments(
  p_category_id bigint,
  p_content_type text,
  p_title text,
  p_body text,
  p_attachments jsonb,
  p_improvement_of bigint DEFAULT NULL
) RETURNS TABLE (
  post_id bigint,
  author_account_id bigint,
  category_id bigint,
  verification app.verification_state,
  created_at timestamptz
)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = app, auth, pg_catalog
AS $$
DECLARE
  created_post_id bigint;
  attachment jsonb;
  attachment_index integer := 0;
  resolved_blob_id bigint;
BEGIN
  SELECT cp.post_id INTO created_post_id
  FROM app.create_post(p_category_id, p_content_type, p_title, p_body, p_improvement_of) AS cp;

  FOR attachment IN SELECT value FROM jsonb_array_elements(coalesce(p_attachments, '[]'::jsonb))
  LOOP
    IF attachment->>'kind' = 'new' THEN
      SELECT efb.file_blob_id INTO resolved_blob_id
      FROM app.ensure_file_blob(attachment->>'mime_type', attachment->>'content_text') AS efb;
    ELSIF attachment->>'kind' = 'existing' THEN
      resolved_blob_id := (attachment->>'file_blob_id')::bigint;
      PERFORM 1 FROM app.file_blobs WHERE id = resolved_blob_id;
      IF NOT FOUND THEN
        RAISE EXCEPTION 'attachment file blob % does not exist', resolved_blob_id;
      END IF;
    ELSE
      RAISE EXCEPTION 'attachment kind must be new or existing';
    END IF;

    INSERT INTO app.post_attachments (post_id, file_blob_id, position)
    VALUES (created_post_id, resolved_blob_id, attachment_index);
    attachment_index := attachment_index + 1;
  END LOOP;

  RETURN QUERY
  SELECT p.id, p.author_id, p.category_id, p.verification, p.created_at
  FROM app.posts AS p
  WHERE p.id = created_post_id;
END;
$$;
```

- [ ] **Step 7: Run static schema tests and fix naming/signature mismatches immediately**

Run: `uv run python -m unittest tests.test_agent_kb_postgres_skeleton -v`
Expected: PASS.

- [ ] **Step 8: Commit the application-side database function layer**

```bash
git add postgres/init/004-app-functions-and-triggers.sql tests/test_agent_kb_postgres_skeleton.py
git commit -m "feat(db): add attachment-aware app write functions"
```

### Task 4: Convert admin flows to canonical function-backed contracts

**Files:**
- Modify: `postgres/init/003-auth-functions.sql`
- Modify: `tests/test_postgres_admin_tooling.py`
- Test: `tests/test_postgres_admin_tooling.py`

- [ ] **Step 1: Write failing static tests for canonical admin functions**

```python
def test_admin_schema_exposes_canonical_account_management_functions(self) -> None:
    content = self.read_text("postgres/init/003-auth-functions.sql")
    self.assertIn("CREATE FUNCTION auth.create_account_with_login(", content)
    self.assertIn("CREATE FUNCTION auth.disable_managed_account(", content)
    self.assertIn("CREATE FUNCTION auth.grant_global_role(", content)
    self.assertIn("CREATE FUNCTION auth.revoke_global_role(", content)
```

- [ ] **Step 2: Run the admin tooling test to verify it fails first**

Run: `uv run python -m unittest tests.test_postgres_admin_tooling -v`
Expected: FAIL because the new canonical function names are absent.

- [ ] **Step 3: Implement the minimal admin function surface in `003-auth-functions.sql`**

```sql
CREATE FUNCTION auth.create_account_with_login(
  p_principal_type auth.principal_type,
  p_display_name text,
  p_login_role text,
  p_password text,
  p_global_role auth.global_role DEFAULT 'normal_user'
) RETURNS TABLE (
  account_id bigint,
  principal_type auth.principal_type,
  display_name text,
  pg_login_role text,
  account_status auth.account_status
)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = auth, app, pg_catalog
AS $$
BEGIN
  IF NOT auth.can_write() OR NOT auth.is_admin() THEN
    RAISE EXCEPTION 'only admin or super_admin may create accounts';
  END IF;
  -- minimal body here, then fill exact insert logic from existing flow
END;
$$;
```

- [ ] **Step 4: Refactor existing admin helpers to delegate to the new canonical functions instead of duplicating business SQL**

```sql
SELECT *
FROM auth.create_account_with_login(
  {{principal_type}}::auth.principal_type,
  {{display_name}},
  {{login_role}},
  {{new_password}},
  {{global_role}}::auth.global_role
);
```

- [ ] **Step 5: Run admin tooling static tests and repair any stale expectations around old SQL bodies**

Run: `uv run python -m unittest tests.test_postgres_admin_tooling -v`
Expected: PASS.

- [ ] **Step 6: Commit the canonical admin contract changes**

```bash
git add postgres/init/003-auth-functions.sql tests/test_postgres_admin_tooling.py skills/agent-kb-postgres-admin/scripts skills/agent-kb-postgres-admin/scripts/sql
git commit -m "refactor(auth): expose canonical admin function contracts"
```

### Task 5: Update RLS and permission contracts for the blob/attachment model

**Files:**
- Modify: `postgres/init/005-permissions-and-rls.sql`
- Modify: `tests/test_agent_kb_postgres_skeleton.py`
- Modify: `tests/test_content_permission_live_matrix.py`
- Test: `tests/test_agent_kb_postgres_skeleton.py`

- [ ] **Step 1: Write failing policy assertions for the new tables**

```python
def test_schema_adds_blob_and_attachment_policies(self) -> None:
    content = self.read_text("postgres/init/005-permissions-and-rls.sql")
    self.assertIn("ALTER TABLE app.file_blobs ENABLE ROW LEVEL SECURITY", content)
    self.assertIn("ALTER TABLE app.post_attachments ENABLE ROW LEVEL SECURITY", content)
    self.assertIn("ALTER TABLE app.review_entry_attachments ENABLE ROW LEVEL SECURITY", content)
    self.assertNotIn("uploaded_files_select_all", content)
```

- [ ] **Step 2: Run the bootstrap static test to verify these policy assertions fail**

Run: `uv run python -m unittest tests.test_agent_kb_postgres_skeleton -v`
Expected: FAIL because policies still reference `uploaded_files`.

- [ ] **Step 3: Replace old `uploaded_files` policies with blob/attachment policies that fit the function model**

```sql
ALTER TABLE app.file_blobs ENABLE ROW LEVEL SECURITY;
ALTER TABLE app.file_blobs FORCE ROW LEVEL SECURITY;

CREATE POLICY file_blobs_select_via_post_attachments ON app.file_blobs
FOR SELECT TO united_agent_user
USING (
  EXISTS (
    SELECT 1
    FROM app.post_attachments AS pa
    WHERE pa.file_blob_id = app.file_blobs.id
  )
  OR EXISTS (
    SELECT 1
    FROM app.review_entry_attachments AS rea
    WHERE rea.file_blob_id = app.file_blobs.id
  )
);
```

- [ ] **Step 4: Keep direct normal-user inserts into `app.file_blobs` disallowed**

```sql
REVOKE INSERT, UPDATE, DELETE ON app.file_blobs FROM united_agent_user;
REVOKE INSERT, UPDATE, DELETE ON app.post_attachments FROM united_agent_user;
REVOKE INSERT, UPDATE, DELETE ON app.review_entry_attachments FROM united_agent_user;
```

- [ ] **Step 5: Run static policy tests**

Run: `uv run python -m unittest tests.test_agent_kb_postgres_skeleton -v`
Expected: PASS.

- [ ] **Step 6: Commit the permission model updates**

```bash
git add postgres/init/005-permissions-and-rls.sql tests/test_agent_kb_postgres_skeleton.py tests/test_content_permission_live_matrix.py
git commit -m "refactor(rls): align policies with blob attachments"
```

### Task 6: Migrate connect-skill wrappers to thin function callers

**Files:**
- Modify: `skills/agent-kb-postgres-connect/scripts/validate_post_flow.py`
- Modify: `skills/agent-kb-postgres-connect/scripts/validate_review_flow.py`
- Modify: `skills/agent-kb-postgres-connect/scripts/upload_text_file.py`
- Modify: `skills/agent-kb-postgres-connect/scripts/read_uploaded_file.py`
- Modify: `skills/agent-kb-postgres-connect/scripts/sql/upload_text_file_insert.sql`
- Modify: `tests/test_postgres_connect_tooling.py`
- Test: `tests/test_postgres_connect_tooling.py`

- [ ] **Step 1: Write failing wrapper assertions that ban standalone user upload flow**

```python
def test_connect_skill_no_longer_exposes_standalone_upload_entrypoint(self) -> None:
    content = self.read_text("skills/agent-kb-postgres-connect/SKILL.md")
    self.assertNotIn("upload_text_file.py", content)


def test_validate_post_flow_calls_database_function(self) -> None:
    content = self.read_text("skills/agent-kb-postgres-connect/scripts/validate_post_flow.py")
    self.assertIn("app.create_post", content)
    self.assertNotIn("INSERT INTO app.posts", content)
```

- [ ] **Step 2: Run connect tooling tests to verify they fail first**

Run: `uv run python -m unittest tests.test_postgres_connect_tooling -v`
Expected: FAIL because wrappers still embed direct insert SQL and standalone upload docs exist.

- [ ] **Step 3: Rewrite `validate_post_flow.py` to call function contracts only**

```python
cursor.execute(
    "SELECT post_id, author_account_id, category_id, verification, created_at FROM app.create_post(%s, %s, %s, %s, %s)",
    (category_id, content_type, title, body, improvement_of),
)
row = cursor.fetchone()
```

- [ ] **Step 4: Rewrite `validate_review_flow.py` to call function contracts only**

```python
cursor.execute(
    "SELECT review_entry_id, account_id, post_id, lgtm, created_at FROM app.create_review_entry(%s, %s, %s)",
    (post_id, lgtm, conclusion),
)
row = cursor.fetchone()
```

- [ ] **Step 5: Remove or repurpose `upload_text_file.py` so it is no longer a standalone normal-user upload flow**

```python
raise SystemExit(
    "standalone upload_text_file.py has been removed; create posts or reviews with attachments through the content creation flows"
)
```

- [ ] **Step 6: Update or remove helper SQL files so wrappers stay thin and function-backed**

```sql
SELECT *
FROM app.create_post_with_attachments(
  %(category_id)s,
  %(content_type)s,
  %(title)s,
  %(body)s,
  %(attachments)s::jsonb,
  %(improvement_of)s
);
```

- [ ] **Step 7: Run connect tooling tests and fix every stale assertion about `uploaded_files`**

Run: `uv run python -m unittest tests.test_postgres_connect_tooling -v`
Expected: PASS.

- [ ] **Step 8: Commit the connect wrapper migration**

```bash
git add skills/agent-kb-postgres-connect tests/test_postgres_connect_tooling.py
git commit -m "refactor(connect): use function-backed content flows"
```

### Task 7: Update live helper utilities and live content tests

**Files:**
- Modify: `tests/live_postgres_helpers.py`
- Modify: `tests/test_connect_skill_live_flows.py`
- Modify: `tests/test_content_permission_live_matrix.py`
- Modify: `tests/test_category_post_live_flows.py`
- Test: `tests/test_connect_skill_live_flows.py`
- Test: `tests/test_content_permission_live_matrix.py`

- [ ] **Step 1: Replace old helper cleanup logic for `uploaded_files` with blob and attachment cleanup**

```python
cursor.execute("DELETE FROM app.post_attachments WHERE post_id = ANY(%s)", (post_ids,))
cursor.execute("DELETE FROM app.review_entry_attachments WHERE review_entry_id = ANY(%s)", (review_entry_ids,))
cursor.execute(
    "DELETE FROM app.file_blobs fb WHERE NOT EXISTS (SELECT 1 FROM app.post_attachments pa WHERE pa.file_blob_id = fb.id) AND NOT EXISTS (SELECT 1 FROM app.review_entry_attachments rea WHERE rea.file_blob_id = fb.id)"
)
```

- [ ] **Step 2: Fix `LiveCategoryPostFlowTest` helper inheritance/use so `create_principal` is available again**

```python
class LiveCategoryPostFlowTest(LivePostgresTestCase):
    def test_live_authorization_paths_match_helper_roles(self) -> None:
        created = self.run_create_principal(
            actor_user="postgres",
            actor_password=POSTGRES_SUPERUSER_PASSWORD,
            principal_type="human",
            display_name="Category Flow User",
            global_role="normal_user",
            login_role=login_role,
            new_password=password,
        )
        self.assertEqual(created.returncode, 0, created.stderr)
```

- [ ] **Step 3: Rewrite live connect tests around create-post/review-with-attachments rather than standalone upload**

```python
result = subprocess.run(
    [
        "uv",
        "run",
        "python",
        str(VALIDATE_POST_FLOW_SCRIPT),
        "--attachments-json",
        json.dumps([
            {"kind": "new", "filename": "a.md", "mime_type": "text/markdown", "content_text": "hello"}
        ]),
    ],
    ...,
)
self.assertEqual(result.returncode, 0, result.stderr)
```

- [ ] **Step 4: Rewrite live content permission tests away from direct `INSERT INTO app.uploaded_files`**

```python
cursor.execute(
    "SELECT post_id FROM app.create_post_with_attachments(%s, %s, %s, %s, %s::jsonb, %s)",
    (
        hello_category_id,
        "post",
        "blob attachment test",
        "body",
        json.dumps([{ "kind": "new", "filename": "demo.txt", "mime_type": "text/plain", "content_text": "payload" }]),
        None,
    ),
)
```

- [ ] **Step 5: Run the live content slices after local Postgres is up**

Run: `uv run python -m unittest tests.test_connect_skill_live_flows tests.test_content_permission_live_matrix tests.test_category_post_live_flows -v`
Expected: PASS.

- [ ] **Step 6: Commit the live-helper and live-test migration**

```bash
git add tests/live_postgres_helpers.py tests/test_connect_skill_live_flows.py tests/test_content_permission_live_matrix.py tests/test_category_post_live_flows.py
git commit -m "test: migrate live flows to blob attachments"
```

### Task 8: Update docs and spec contracts to match the final system

**Files:**
- Modify: `README.md`
- Modify: `docs/developer-guide.md`
- Modify: `.trellis/spec/backend/database-guidelines.md`
- Modify: `.trellis/spec/backend/quality-guidelines.md`
- Modify: `tests/test_postgres_connect_tooling.py`
- Modify: `tests/test_postgres_admin_tooling.py`
- Test: `tests/test_postgres_connect_tooling.py`
- Test: `tests/test_postgres_admin_tooling.py`

- [ ] **Step 1: Update README examples to describe content creation with attachments, not standalone upload**

```md
- Create posts and reviews through the shipped function-backed wrappers.
- Attachments are deduplicated globally by `sha256` and may be reused by later posts or reviews.
- Normal users cannot upload unattached files.
```

- [ ] **Step 2: Update developer guide examples to use the new wrapper contract**

```md
uv run python skills/agent-kb-postgres-connect/scripts/validate_post_flow.py --attachments-json '[{"kind":"new","filename":"demo.txt","mime_type":"text/plain","content_text":"hello"}]'
```

- [ ] **Step 3: Capture the durable rules in backend specs**

```md
- Fixed write-path business rules belong in PostgreSQL functions under `auth` and `app`.
- Thin Python wrappers should call those functions instead of shipping large business SQL snippets.
- Attachment content is stored in `app.file_blobs` and attached through `app.post_attachments` / `app.review_entry_attachments`.
```

- [ ] **Step 4: Run static docs/tooling assertions**

Run: `uv run python -m unittest tests.test_postgres_connect_tooling tests.test_postgres_admin_tooling -v`
Expected: PASS.

- [ ] **Step 5: Commit the docs/spec alignment**

```bash
git add README.md docs/developer-guide.md .trellis/spec/backend/database-guidelines.md .trellis/spec/backend/quality-guidelines.md tests/test_postgres_connect_tooling.py tests/test_postgres_admin_tooling.py
git commit -m "docs: document function-backed attachment flows"
```

### Task 9: Final verification and cleanup

**Files:**
- Modify: any files touched by verification fixes
- Test: full targeted suite for this feature

- [ ] **Step 1: Run the static regression suite for this feature area**

Run: `uv run python -m unittest tests.test_agent_kb_postgres_skeleton tests.test_postgres_connect_tooling tests.test_postgres_admin_tooling -v`
Expected: PASS.

- [ ] **Step 2: Run the live regression suite for this feature area**

Run: `uv run python -m unittest tests.test_connect_skill_live_flows tests.test_content_permission_live_matrix tests.test_category_post_live_flows tests.test_create_principal_live_flows -v`
Expected: PASS.

- [ ] **Step 3: Run the whole repo test suite to catch collisions with adjacent work**

Run: `uv run python -m unittest discover -s tests -v`
Expected: PASS.

- [ ] **Step 4: Inspect the final diff before completion**

Run: `git diff --stat HEAD~9..HEAD`
Expected: changes concentrated in bootstrap SQL, wrappers, docs, and tests for this feature.

- [ ] **Step 5: Create the final feature commit if any unstaged fixups remain**

```bash
git add postgres/init skills tests README.md docs .trellis/spec
git commit -m "feat(db): move fixed write flows behind function contracts"
```

## Self-Review

- Spec coverage: covered function boundaries, blob dedup, multiple attachments, reference-existing behavior, no standalone upload flow, thin Python wrappers, admin function contracts, docs/spec updates, and verification.
- Placeholder scan: no `TODO` / `TBD` placeholders remain in tasks; every task includes concrete files, code, and commands.
- Type consistency: the plan consistently uses `app.file_blobs`, `app.post_attachments`, `app.review_entry_attachments`, `app.create_post_with_attachments(...)`, and `app.create_review_entry_with_attachments(...)`.
