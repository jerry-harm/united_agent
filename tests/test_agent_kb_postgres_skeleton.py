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
            "CREATE FUNCTION auth.has_global_role(role_name auth.global_role)",
            "CREATE FUNCTION auth.is_board_moderator(target_board_id bigint)",
            "CREATE FUNCTION auth.can_write()",
            "CREATE FUNCTION auth.create_account_login(",
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
            "USING (auth.can_write() AND (auth.is_admin() OR auth.is_board_moderator(board_id)))",
            "WITH CHECK (auth.can_write() AND (auth.is_admin() OR auth.is_board_moderator(board_id)))",
            "USING (auth.can_write() AND account_id = auth.current_account_id())",
            "USING (auth.can_write() AND auth.is_admin());",
        ):
            self.assertIn(expected, content)

    def test_old_bootstrap_sql_name_is_removed_from_live_paths(self) -> None:
        self.assertFalse((ROOT / "postgres/init/001-agent-knowledge-base.sql").exists())

    def test_bootstrap_skill_documents_connection_flow(self) -> None:
        content = self.read_text("skills/agent-kb-postgres-connect/SKILL.md")

        self.assertIn("name: agent-kb-postgres-connect", content)
        self.assertIn("already running PostgreSQL-backed agent knowledge base server", content)
        self.assertIn("It does not cover:", content)
        self.assertIn("starting the PostgreSQL server", content)
        self.assertIn("psql postgresql://<ADMIN_LOGIN_ROLE>:<ADMIN_PASSWORD>@<DB_HOST>:<DB_PORT>/<DB_NAME>", content)
        self.assertIn("auth.accounts", content)
        self.assertIn("auth.principal_global_roles", content)
        self.assertIn("auth.create_account_login", content)
        self.assertIn("psql postgresql://<NEW_LOGIN_ROLE>:<NEW_LOGIN_PASSWORD>@<DB_HOST>:<DB_PORT>/<DB_NAME>", content)
        self.assertIn("SELECT current_user, session_user, auth.current_account_id(), auth.current_account_status();", content)
        self.assertIn("united_agent", content)
        self.assertIn("united_agent_user", content)


if __name__ == "__main__":
    unittest.main()
