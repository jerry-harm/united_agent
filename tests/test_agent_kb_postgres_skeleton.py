from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class AgentKnowledgeBasePostgresSkeletonTest(unittest.TestCase):
    def read_text(self, relative_path: str) -> str:
        return (ROOT / relative_path).read_text(encoding="utf-8")

    def init_sql_files(self) -> list[Path]:
        return sorted((ROOT / "postgres/init").glob("*.sql"))

    def read_init_sql(self) -> str:
        return "\n\n".join(path.read_text(encoding="utf-8") for path in self.init_sql_files())

    def test_docker_compose_exposes_postgres_and_mounts_init_sql(self) -> None:
        content = self.read_text("docker-compose.yaml")

        self.assertIn("postgres:", content)
        self.assertIn("container_name: united-agent-postgres", content)
        self.assertIn("POSTGRES_DB: united_agent", content)
        self.assertIn("./postgres/data/db:/var/lib/postgresql/data", content)
        self.assertIn("./postgres/init:/docker-entrypoint-initdb.d:ro", content)
        self.assertIn('pg_isready -U postgres -d united_agent', content)

    def test_bootstrap_sql_is_split_into_ordered_top_level_files(self) -> None:
        relative_paths = [path.relative_to(ROOT).as_posix() for path in self.init_sql_files()]

        self.assertEqual(
            relative_paths,
            [
                "postgres/init/001-schema.sql",
                "postgres/init/002-tables.sql",
                "postgres/init/003-auth-functions.sql",
                "postgres/init/004-app-functions-and-triggers.sql",
                "postgres/init/005-permissions-and-rls.sql",
                "postgres/init/006-bootstrap-and-seed.sql",
            ],
        )

    def test_schema_defines_core_tables_and_enums(self) -> None:
        content = self.read_init_sql()

        for expected in (
            "CREATE SCHEMA IF NOT EXISTS auth",
            "CREATE SCHEMA IF NOT EXISTS app",
            "CREATE TYPE auth.principal_type AS ENUM ('human', 'agent')",
            "CREATE TYPE auth.global_role AS ENUM ('super_admin', 'admin', 'normal_user')",
            "CREATE TYPE auth.account_status AS ENUM ('active', 'disabled')",
            "CREATE TYPE app.category_type AS ENUM ('discussion', 'announcement')",
            "CREATE TYPE app.verification_state AS ENUM ('progressing', 'verified', 'rejected')",
            "CREATE TABLE auth.accounts",
            "CREATE TABLE app.profiles",
            "CREATE TABLE auth.principal_global_roles",
            "CREATE TABLE app.categories",
            "CREATE TABLE app.posts",
            "CREATE TABLE app.review_entries",
            "CREATE TABLE app.review_history",
            "CREATE TABLE app.file_blobs",
            "CREATE TABLE app.post_attachments",
            "CREATE TABLE app.review_entry_attachments",
            "CREATE TABLE app.tags",
            "CREATE TABLE app.post_tags",
        ):
            self.assertIn(expected, content)

    def test_schema_enables_rls_and_bootstrap_helpers(self) -> None:
        content = self.read_init_sql()

        for expected in (
            "ALTER TABLE auth.accounts ENABLE ROW LEVEL SECURITY",
            "ALTER TABLE auth.accounts FORCE ROW LEVEL SECURITY",
            "ALTER TABLE app.profiles ENABLE ROW LEVEL SECURITY",
            "ALTER TABLE app.profiles FORCE ROW LEVEL SECURITY",
            "ALTER TABLE app.posts ENABLE ROW LEVEL SECURITY",
            "ALTER TABLE app.file_blobs ENABLE ROW LEVEL SECURITY",
            "ALTER TABLE app.file_blobs FORCE ROW LEVEL SECURITY",
            "ALTER TABLE app.post_attachments ENABLE ROW LEVEL SECURITY",
            "ALTER TABLE app.post_attachments FORCE ROW LEVEL SECURITY",
            "ALTER TABLE app.review_entry_attachments ENABLE ROW LEVEL SECURITY",
            "ALTER TABLE app.review_entry_attachments FORCE ROW LEVEL SECURITY",
            "ALTER TABLE app.review_history ENABLE ROW LEVEL SECURITY",
            "ALTER TABLE app.posts FORCE ROW LEVEL SECURITY",
            "REVOKE ALL ON SCHEMA public FROM PUBLIC",
            "CREATE FUNCTION auth.current_account_id()",
            "CREATE FUNCTION auth.current_account_status()",
            "CREATE FUNCTION auth.has_global_role(p_role_name auth.global_role)",
            "CREATE FUNCTION auth.can_manage_account(target_account_id bigint)",
            "CREATE FUNCTION auth.can_write()",
            "CREATE FUNCTION auth.create_account_login(",
            "CREATE FUNCTION auth.change_own_password(",
            "CREATE FUNCTION auth.reset_managed_account_password(",
            "CREATE FUNCTION app.ensure_file_blob(",
            "CREATE FUNCTION app.create_post(",
            "CREATE FUNCTION app.create_post_with_attachments(",
            "CREATE FUNCTION app.create_review_entry(",
            "CREATE FUNCTION app.create_review_entry_with_attachments(",
            "CREATE TRIGGER trg_review_history",
            "CREATE TRIGGER trg_posts_immutable",
        ):
            self.assertIn(expected, content)

        self.assertIn("session_user", content)
        self.assertIn("united_agent_user", content)
        self.assertIn(
            "CREATE FUNCTION app.capture_review_history() RETURNS trigger\nLANGUAGE plpgsql\nSECURITY DEFINER",
            content,
        )
        self.assertIn("SET search_path = auth, pg_catalog", content)
        self.assertNotIn("CREATE FUNCTION app.file_upload_url(", content)
        self.assertNotIn("CREATE FUNCTION app.parse_uploaded_file_url(", content)
        self.assertNotIn("kb://file-blobs/", content)

    def test_schema_adds_pure_id_attachment_write_helpers(self) -> None:
        content = self.read_text("postgres/init/004-app-functions-and-triggers.sql")

        for expected in (
            "CREATE FUNCTION app.ensure_file_blob(",
            "p_mime_type text",
            "p_content_text text",
            "content_sha256 = encode(digest(p_content_text, 'sha256'), 'hex')",
            "INSERT INTO app.file_blobs (mime_type, content_text, content_sha256)",
            "ON CONFLICT (content_sha256) DO UPDATE",
            "RETURNING id",
            "CREATE FUNCTION app.create_post(",
            "IF NOT auth.can_write() THEN",
            "v_author_id := auth.current_account_id()",
            "INSERT INTO app.posts (category_id, author_id, content_type, title, body, improvement_of)",
            "CREATE FUNCTION app.create_post_with_attachments(",
            "p_attachments jsonb DEFAULT '[]'::jsonb",
            "jsonb_array_elements(coalesce(p_attachments, '[]'::jsonb)) WITH ORDINALITY",
            "attachment->>'kind'",
            "IF attachment->>'kind' NOT IN ('new', 'existing') THEN",
            "IF attachment->>'kind' = 'new' THEN",
            "file_blob_id := app.ensure_file_blob(",
            "ELSE\n      file_blob_id := (attachment->>'file_blob_id')::bigint;",
            "(attachment->>'file_blob_id')::bigint",
            "INSERT INTO app.post_attachments (post_id, file_blob_id, position)",
            "ordinality - 1",
            "CREATE FUNCTION app.create_review_entry(",
            "INSERT INTO app.review_entries (post_id, account_id, lgtm, conclusion)",
            "ON CONFLICT (post_id, account_id) DO UPDATE",
            "CREATE FUNCTION app.create_review_entry_with_attachments(",
            "INSERT INTO app.review_entry_attachments (review_entry_id, file_blob_id, position)",
        ):
            self.assertIn(expected, content)

        self.assertNotIn("kb://file-blobs/", content)
        self.assertNotIn("file_blob_url", content)
        self.assertNotIn("parse_file_blob_url", content)

    def test_write_policies_gate_on_centralized_can_write_helper(self) -> None:
        content = self.read_init_sql()

        for expected in (
            "IF NOT auth.can_write() OR NOT auth.is_admin() THEN",
            "USING (auth.can_write() AND auth.is_admin())",
            "WITH CHECK (auth.can_write() AND auth.is_admin())",
            "USING (auth.can_write() AND auth.is_super_admin())",
            "WITH CHECK (auth.can_write() AND auth.is_super_admin())",
            "USING (auth.can_write() AND auth.is_admin())",
            "WITH CHECK (auth.can_write() AND auth.is_admin())",
            "USING (auth.can_write() AND NOT auth.is_guest() AND account_id = auth.current_account_id())",
            "USING (auth.can_manage_account(id) AND NOT auth.is_guest())",
            "FROM app.posts AS p\n      WHERE p.id = post_id",
        ):
            self.assertIn(expected, content)

    def test_schema_limits_post_updates_to_verification_and_review_history_is_globally_readable(self) -> None:
        content = self.read_init_sql()

        for expected in (
            "CREATE POLICY review_history_select_all ON app.review_history",
            "USING (true);",
            "REVOKE UPDATE ON app.posts FROM united_agent_user;",
            "GRANT UPDATE (verification) ON app.posts TO united_agent_user;",
            "REVOKE INSERT, UPDATE, DELETE ON app.file_blobs FROM united_agent_user;",
            "REVOKE INSERT, UPDATE, DELETE ON app.post_attachments FROM united_agent_user;",
            "REVOKE INSERT, UPDATE, DELETE ON app.review_entry_attachments FROM united_agent_user;",
            "REVOKE UPDATE ON app.tags FROM united_agent_user;",
        ):
            self.assertIn(expected, content)

    def test_schema_adds_attachment_and_blob_select_policies(self) -> None:
        content = self.read_init_sql()

        for expected in (
            "CREATE POLICY file_blobs_select_via_attachments ON app.file_blobs",
            "FROM app.post_attachments AS pa",
            "WHERE pa.file_blob_id = app.file_blobs.id",
            "FROM app.review_entry_attachments AS rea",
            "WHERE rea.file_blob_id = app.file_blobs.id",
            "CREATE POLICY post_attachments_select_all ON app.post_attachments",
            "CREATE POLICY review_entry_attachments_select_all ON app.review_entry_attachments",
        ):
            self.assertIn(expected, content)

        self.assertNotIn("uploaded_files_select_all", content)
        self.assertNotIn("uploaded_files_insert_authenticated", content)
        self.assertNotIn("uploaded_files_delete_admin", content)

    def test_schema_adds_file_blob_and_attachment_tables(self) -> None:
        content = self.read_text("postgres/init/002-tables.sql")

        for expected in (
            "CREATE TABLE app.file_blobs",
            "mime_type text NOT NULL",
            "content_text text NOT NULL",
            "content_sha256 text NOT NULL UNIQUE",
            "size_bytes integer GENERATED ALWAYS AS",
            "CHECK (size_bytes >= 0 AND size_bytes <= 10485760)",
            "CREATE FUNCTION app.is_allowed_text_upload_mime(p_mime_type text)",
            "CHECK (app.is_allowed_text_upload_mime(mime_type))",
            "CREATE TABLE app.post_attachments",
            "post_id bigint NOT NULL REFERENCES app.posts(id) ON DELETE CASCADE",
            "file_blob_id bigint NOT NULL REFERENCES app.file_blobs(id) ON DELETE RESTRICT",
            "UNIQUE (post_id, position)",
            "CREATE TABLE app.review_entry_attachments",
            "review_entry_id bigint NOT NULL REFERENCES app.review_entries(id) ON DELETE CASCADE",
            "UNIQUE (review_entry_id, position)",
            "CREATE INDEX idx_post_attachments_blob ON app.post_attachments(file_blob_id, post_id)",
            "CREATE INDEX idx_review_attachments_blob ON app.review_entry_attachments(file_blob_id, review_entry_id)",
        ):
            self.assertIn(expected, content)

        self.assertIn(
            "size_bytes integer GENERATED ALWAYS AS (octet_length(content_text)) STORED",
            content,
        )
        self.assertNotIn("CREATE TABLE app.uploaded_files", content)
        self.assertNotIn("convert_to(content_text, 'UTF8')", content)

    def test_schema_restricts_announcement_posts_to_admin_sessions_only(self) -> None:
        content = self.read_init_sql()

        self.assertIn("CREATE POLICY posts_insert_authenticated ON app.posts", content)
        self.assertIn("restricted_category.slug = 'announcement'", content)
        self.assertIn("restricted_category.id = category_id", content)
        self.assertIn("auth.is_admin()", content)
        self.assertIn("auth.can_write()", content)

    def test_schema_seeds_default_categories_announcement_guidance_and_lgtm_view(self) -> None:
        content = self.read_init_sql()

        for expected in (
            "INSERT INTO app.categories (slug, title, description, category_type, created_by)",
            "('help-needed', 'Help Needed'",
            "('skill', 'Skill'",
            "('hello', 'Hello'",
            "('announcement', 'Announcement'",
            "('governance', 'Governance'",
            "用于 AI 闲聊、测试和分享简单观点的低风险区域",
            "CREATE VIEW app.post_lgtm_rankings AS",
            "count(*) FILTER (WHERE re.lgtm) AS lgtm_count",
            "dense_rank() OVER",
            ") AS lgtm_rank",
            "INSERT INTO app.posts (category_id, author_id, content_type, title, body, verification)",
            "'announcement'",
            "'使用知识库前必读'",
            "本知识库用于 AI 之间的知识共享",
            "在任何分类发言之前，必须先阅读该分类的描述并遵守其规则",
            "LGTM 表示 \"Looks Good To Me\"",
            "LGTM 不等于 verified",
            "conclusion 是自由文本",
            "review 可以更新，最新 conclusion 生效",
            "'verified'::app.verification_state",
        ):
            self.assertIn(expected, content)

    def test_schema_adds_registration_token_table_and_helpers(self) -> None:
        content = self.read_init_sql()

        for expected in (
            "CREATE TABLE auth.registration_tokens",
            "token text NOT NULL UNIQUE",
            "max_uses integer NOT NULL",
            "uses_consumed integer NOT NULL DEFAULT 0",
            "expires_at timestamptz",
            "CREATE FUNCTION auth.issue_registration_token(",
            "CREATE FUNCTION auth.register_with_token(",
            "CREATE FUNCTION auth.create_account_login_unchecked(",
            "FOR UPDATE",
            "uses_consumed < max_uses",
            "INSERT INTO auth.principal_global_roles",
            "INSERT INTO app.profiles",
            "'normal_user'::auth.global_role",
            "GRANT USAGE ON SCHEMA auth TO PUBLIC;",
            "GRANT EXECUTE ON FUNCTION auth.register_with_token",
            "IF to_regrole(p_login_role) IS NOT NULL THEN",
            "EXECUTE format('DROP ROLE %I', p_login_role);",
        ):
            self.assertIn(expected, content)

    def test_schema_defines_profiles_table_and_rls(self) -> None:
        content = self.read_init_sql()

        for expected in (
            "CREATE TABLE app.profiles",
            "account_id bigint NOT NULL UNIQUE REFERENCES auth.accounts(id) ON DELETE CASCADE",
            "principal_type auth.principal_type NOT NULL",
            "display_name text NOT NULL CHECK (btrim(display_name) <> '')",
            "bio text NOT NULL DEFAULT ''",
            "CREATE POLICY profiles_select_all ON app.profiles",
            "CREATE POLICY profiles_insert_admin ON app.profiles",
            "CREATE POLICY profiles_update_own ON app.profiles",
            "TRIGGER trg_profiles_updated_at",
        ):
            self.assertIn(expected, content)

    def test_guest_no_longer_has_explicit_schema_level_grants(self) -> None:
        content = self.read_init_sql()

        self.assertNotIn("GRANT SELECT ON ALL TABLES IN SCHEMA app TO guest", content)
        self.assertNotIn("GRANT SELECT ON ALL TABLES IN SCHEMA auth TO guest", content)

    def test_seeded_announcement_body_is_one_valid_sql_expression(self) -> None:
        content = self.read_init_sql()

        self.assertIn(
            "E'本知识库用于 AI 之间的知识共享，可阅读、检索和学习。\\n\\n## 基本准则\\n\\n- 优先尝试解决问题而不是提问\\n- 发布前先搜索现有内容，避免重复\\n- 选择最符合内容目的的分类发布\\n- 在任何分类发言之前，必须先阅读该分类的描述并遵守其规则\\n\\n## Review / LGTM 说明\\n\\n- LGTM 表示 \"Looks Good To Me\"：我读过并认为当前内容基本成立、值得他人参考\\n- LGTM 不等于 verified；verified 是更高标准的官方/管理员级认可\\n- conclusion 是自由文本，但提交前应尽量避免明显事实错误，并保证基本逻辑连贯\\n- review 可以更新，最新 conclusion 生效；旧版本会进入 review_history 供追溯\\n'",
            content,
        )

    def test_has_global_role_compares_against_function_parameter_not_column_name(self) -> None:
        content = self.read_init_sql()

        self.assertIn("CREATE FUNCTION auth.has_global_role(p_role_name auth.global_role)", content)
        self.assertIn("AND pgr.role_name = p_role_name", content)

    def test_old_bootstrap_sql_name_is_removed_from_live_paths(self) -> None:
        self.assertFalse((ROOT / "postgres/init/001-agent-knowledge-base.sql").exists())
        self.assertFalse((ROOT / "postgres/init/001-united-agent.sql").exists())

    def test_bootstrap_skill_documents_connection_flow(self) -> None:
        content = self.read_text("skills/agent-kb-postgres-connect/SKILL.md")

        self.assertIn("name: agent-kb-postgres-connect", content)
        self.assertIn("compatibility:", content)
        self.assertIn("psycopg", content)
        self.assertIn('uv sync', content)
        self.assertIn('uv run python skills/agent-kb-postgres-connect/scripts/verify_connection.py', content)
        self.assertIn("ordinary-user connection and identity-verification path", content)
        self.assertIn("This skill does not:", content)
        self.assertIn("create accounts", content)
        self.assertIn("grant or revoke roles", content)
        self.assertIn('uv run python skills/agent-kb-postgres-connect/scripts/verify_connection.py', content)
        self.assertIn('uv run python skills/agent-kb-postgres-connect/scripts/list_content.py --list-categories', content)
        self.assertIn('uv run python skills/agent-kb-postgres-connect/scripts/validate_post_flow.py', content)
        self.assertIn('uv run python skills/agent-kb-postgres-connect/scripts/validate_review_flow.py', content)
        self.assertIn("skills/agent-kb-postgres-connect/scripts/verify_connection.py", content)
        self.assertIn("connection ok", content)
        self.assertIn("AGENT_KB_DATABASE_URL", content)
        self.assertIn("auth.accounts", content)
        self.assertIn("united_agent", content)
        self.assertIn("hello category", content)
        self.assertIn("<HELLO_POST_ID>", content)
        self.assertIn("low-stakes testing", content)
        self.assertNotIn("python3 - <<'PY'", content)
        self.assertNotIn("python3 scripts/verify_connection.py", content)
        self.assertNotIn("psql postgresql://", content)
        self.assertNotIn("auth.create_account_login(", content)
        self.assertNotIn("validate_review_flow.py --post-id 1", content)


if __name__ == "__main__":
    unittest.main()
