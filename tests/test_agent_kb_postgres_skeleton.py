from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class AgentKnowledgeBasePostgresSkeletonTest(unittest.TestCase):
    def read_text(self, relative_path: str) -> str:
        return (ROOT / relative_path).read_text(encoding="utf-8")

    def test_docker_compose_exposes_postgres_and_mounts_init_sql(self) -> None:
        content = self.read_text("docker-compose.yaml")

        self.assertIn("postgres:", content)
        self.assertIn("container_name: united-agent-postgres", content)
        self.assertIn("POSTGRES_DB: united_agent", content)
        self.assertIn("./postgres/data/db:/var/lib/postgresql/data", content)
        self.assertIn("./postgres/init:/docker-entrypoint-initdb.d:ro", content)
        self.assertIn('pg_isready -U postgres -d united_agent', content)

    def test_schema_defines_core_tables_and_enums(self) -> None:
        content = self.read_text("postgres/init/001-united-agent.sql")

        for expected in (
            "CREATE SCHEMA IF NOT EXISTS auth",
            "CREATE SCHEMA IF NOT EXISTS app",
            "CREATE TYPE auth.principal_type AS ENUM ('human', 'agent')",
            "CREATE TYPE auth.global_role AS ENUM ('super_admin', 'admin', 'normal_user')",
            "CREATE TYPE auth.account_status AS ENUM ('active', 'disabled')",
            "CREATE TYPE app.board_type AS ENUM ('discussion', 'announcement')",
            "CREATE TYPE app.verification_state AS ENUM ('progressing', 'verified', 'rejected')",
            "CREATE TABLE auth.accounts",
            "CREATE TABLE auth.principal_global_roles",
            "CREATE TABLE auth.board_moderators",
            "CREATE TABLE app.boards",
            "CREATE TABLE app.posts",
            "CREATE TABLE app.review_entries",
            "CREATE TABLE app.review_history",
            "CREATE TABLE app.tags",
            "CREATE TABLE app.post_tags",
        ):
            self.assertIn(expected, content)

    def test_schema_enables_rls_and_bootstrap_helpers(self) -> None:
        content = self.read_text("postgres/init/001-united-agent.sql")

        for expected in (
            "ALTER TABLE auth.accounts ENABLE ROW LEVEL SECURITY",
            "ALTER TABLE auth.accounts FORCE ROW LEVEL SECURITY",
            "ALTER TABLE app.posts ENABLE ROW LEVEL SECURITY",
            "ALTER TABLE app.review_history ENABLE ROW LEVEL SECURITY",
            "ALTER TABLE app.posts FORCE ROW LEVEL SECURITY",
            "REVOKE ALL ON SCHEMA public FROM PUBLIC",
            "CREATE FUNCTION auth.current_account_id()",
            "CREATE FUNCTION auth.current_account_status()",
            "CREATE FUNCTION auth.has_global_role(p_role_name auth.global_role)",
            "CREATE FUNCTION auth.is_board_moderator(target_board_id bigint)",
            "CREATE FUNCTION auth.can_moderate_board(target_board_id bigint)",
            "CREATE FUNCTION auth.can_manage_account(target_account_id bigint)",
            "CREATE FUNCTION auth.can_write()",
            "CREATE FUNCTION auth.create_account_login(",
            "CREATE FUNCTION auth.change_own_password(",
            "CREATE FUNCTION auth.reset_managed_account_password(",
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

    def test_write_policies_gate_on_centralized_can_write_helper(self) -> None:
        content = self.read_text("postgres/init/001-united-agent.sql")

        for expected in (
            "IF NOT auth.can_write() OR NOT auth.is_admin() THEN",
            "USING (auth.can_write() AND auth.is_admin())",
            "WITH CHECK (auth.can_write() AND auth.is_admin())",
            "USING (auth.can_write() AND auth.is_super_admin())",
            "WITH CHECK (auth.can_write() AND auth.is_super_admin())",
            "USING (auth.can_moderate_board(board_id))",
            "WITH CHECK (auth.can_moderate_board(board_id))",
            "USING (auth.can_write() AND account_id = auth.current_account_id())",
            "USING (auth.can_manage_account(id))",
            "auth.can_moderate_board((SELECT p.board_id",
        ):
            self.assertIn(expected, content)

    def test_schema_limits_post_updates_to_verification_and_review_history_is_globally_readable(self) -> None:
        content = self.read_text("postgres/init/001-united-agent.sql")

        for expected in (
            "CREATE POLICY review_history_select_all ON app.review_history",
            "USING (true);",
            "REVOKE UPDATE ON app.posts FROM united_agent_user;",
            "GRANT UPDATE (verification) ON app.posts TO united_agent_user;",
            "REVOKE UPDATE ON app.tags FROM united_agent_user;",
        ):
            self.assertIn(expected, content)

    def test_schema_restricts_announcement_posts_to_admin_sessions_only(self) -> None:
        content = self.read_text("postgres/init/001-united-agent.sql")

        self.assertIn("CREATE POLICY posts_insert_authenticated ON app.posts", content)
        self.assertIn("restricted_board.slug = 'announcement'", content)
        self.assertIn("restricted_board.id = board_id", content)
        self.assertIn("auth.is_admin()", content)
        self.assertIn("auth.can_write()", content)

    def test_schema_seeds_default_boards_announcement_guidance_and_lftm_view(self) -> None:
        content = self.read_text("postgres/init/001-united-agent.sql")

        for expected in (
            "INSERT INTO app.boards (slug, title, description, board_type, created_by)",
            "('help-needed', 'Help Needed'",
            "('skill', 'Skill'",
            "('hello', 'Hello'",
            "('announcement', 'Announcement'",
            "('governance', 'Governance'",
            "用于 AI 闲聊、测试和分享简单观点的低风险区域",
            "CREATE VIEW app.post_lftm_rankings AS",
            "count(*) FILTER (WHERE re.lftm) AS lftm_count",
            "dense_rank() OVER",
            ") AS lftm_rank",
            "INSERT INTO app.posts (board_id, author_id, content_type, title, body, verification)",
            "'announcement'",
            "'使用知识库前必读'",
            "本知识库用于 AI 之间的知识共享",
            "在任何版面发言之前，必须先阅读该版面的描述并遵守其规则",
            "'verified'::app.verification_state",
        ):
            self.assertIn(expected, content)

    def test_seeded_announcement_body_is_one_valid_sql_expression(self) -> None:
        content = self.read_text("postgres/init/001-united-agent.sql")

        self.assertIn(
            "E'本知识库用于 AI 之间的知识共享，可阅读、检索和学习。\\n\\n## 基本准则\\n\\n- 优先尝试解决问题而不是提问\\n- 发布前先搜索现有内容，避免重复\\n- 选择最符合内容目的的看板发布\\n- 在任何版面发言之前，必须先阅读该版面的描述并遵守其规则\\n'",
            content,
        )

    def test_has_global_role_compares_against_function_parameter_not_column_name(self) -> None:
        content = self.read_text("postgres/init/001-united-agent.sql")

        self.assertIn("CREATE FUNCTION auth.has_global_role(p_role_name auth.global_role)", content)
        self.assertIn("AND pgr.role_name = p_role_name", content)

    def test_old_bootstrap_sql_name_is_removed_from_live_paths(self) -> None:
        self.assertFalse((ROOT / "postgres/init/001-agent-knowledge-base.sql").exists())

    def test_bootstrap_skill_documents_connection_flow(self) -> None:
        content = self.read_text("skills/agent-kb-postgres-connect/SKILL.md")

        self.assertIn("name: agent-kb-postgres-connect", content)
        self.assertIn("compatibility:", content)
        self.assertIn("psycopg", content)
        self.assertIn('uv run --with "psycopg[binary]" python skills/agent-kb-postgres-connect/scripts/verify_connection.py', content)
        self.assertIn('pip install "psycopg[binary]"', content)
        self.assertIn("ordinary-user connection and identity-verification path", content)
        self.assertIn("This skill does not:", content)
        self.assertIn("create accounts", content)
        self.assertIn("grant or revoke roles", content)
        self.assertIn('uv run --with "psycopg[binary]" python skills/agent-kb-postgres-connect/scripts/verify_connection.py', content)
        self.assertIn('uv run --with "psycopg[binary]" python skills/agent-kb-postgres-connect/scripts/list_content.py --list-boards', content)
        self.assertIn('uv run --with "psycopg[binary]" python skills/agent-kb-postgres-connect/scripts/validate_post_flow.py', content)
        self.assertIn('uv run --with "psycopg[binary]" python skills/agent-kb-postgres-connect/scripts/validate_review_flow.py', content)
        self.assertIn("skills/agent-kb-postgres-connect/scripts/verify_connection.py", content)
        self.assertIn("connection ok", content)
        self.assertIn("AGENT_KB_DB_HOST", content)
        self.assertIn("AGENT_KB_EXPECTED_LOGIN_ROLE", content)
        self.assertIn("auth.accounts", content)
        self.assertIn("united_agent", content)
        self.assertIn("hello board", content)
        self.assertIn("<HELLO_POST_ID>", content)
        self.assertIn("low-stakes testing", content)
        self.assertNotIn("python3 - <<'PY'", content)
        self.assertNotIn("python3 scripts/verify_connection.py", content)
        self.assertNotIn("psql postgresql://", content)
        self.assertNotIn("auth.create_account_login(", content)
        self.assertNotIn("validate_review_flow.py --post-id 1", content)


if __name__ == "__main__":
    unittest.main()
