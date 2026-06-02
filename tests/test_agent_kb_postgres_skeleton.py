from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class AgentKnowledgeBasePostgresSkeletonTest(unittest.TestCase):
    def read_text(self, relative_path: str) -> str:
        return (ROOT / relative_path).read_text(encoding="utf-8")

    def test_docker_compose_exposes_postgres_and_mounts_init_sql(self) -> None:
        content = self.read_text("docker-compose.yaml")

        self.assertIn("postgres:", content)
        self.assertIn("POSTGRES_DB: agent_knowledge_base", content)
        self.assertIn("./postgres/data/db:/var/lib/postgresql/data", content)
        self.assertIn("./postgres/init:/docker-entrypoint-initdb.d:ro", content)

    def test_schema_defines_core_tables_and_enums(self) -> None:
        content = self.read_text("postgres/init/001-agent-knowledge-base.sql")

        for expected in (
            "CREATE TYPE app.principal_type AS ENUM ('human', 'agent')",
            "CREATE TYPE app.business_role AS ENUM ('super_admin', 'admin', 'normal_user')",
            "CREATE TYPE app.board_type AS ENUM ('discussion', 'announcement')",
            "CREATE TYPE app.verification_state AS ENUM ('progressing', 'verified', 'rejected')",
            "CREATE TABLE app.principals",
            "CREATE TABLE app.boards",
            "CREATE TABLE app.board_moderators",
            "CREATE TABLE app.posts",
            "CREATE TABLE app.review_entries",
            "CREATE TABLE app.review_history",
            "CREATE TABLE app.tags",
            "CREATE TABLE app.post_tags",
        ):
            self.assertIn(expected, content)

    def test_schema_enables_rls_and_bootstrap_helpers(self) -> None:
        content = self.read_text("postgres/init/001-agent-knowledge-base.sql")

        for expected in (
            "ALTER TABLE app.posts ENABLE ROW LEVEL SECURITY",
            "ALTER TABLE app.review_history ENABLE ROW LEVEL SECURITY",
            "CREATE FUNCTION app.current_principal_id()",
            "CREATE FUNCTION app.current_business_role()",
            "CREATE FUNCTION app.is_board_moderator(target_board_id bigint)",
            "CREATE FUNCTION app.bootstrap_principal(",
            "CREATE TRIGGER trg_review_history",
            "CREATE TRIGGER trg_posts_immutable",
        ):
            self.assertIn(expected, content)

        self.assertIn("session_user", content)
        self.assertIn(
            "CREATE FUNCTION app.capture_review_history() RETURNS trigger\nLANGUAGE plpgsql\nSECURITY DEFINER",
            content,
        )

    def test_bootstrap_skill_documents_connection_flow(self) -> None:
        content = self.read_text("skills/agent-kb-postgres-connect/SKILL.md")

        self.assertIn("name: agent-kb-postgres-connect", content)
        self.assertIn("already running PostgreSQL-backed agent knowledge base server", content)
        self.assertIn("It does not cover:", content)
        self.assertIn("starting the PostgreSQL server", content)
        self.assertIn("psql postgresql://<ADMIN_LOGIN_ROLE>:<ADMIN_PASSWORD>@<DB_HOST>:<DB_PORT>/<DB_NAME>", content)
        self.assertIn("'<NEW_LOGIN_ROLE>'", content)
        self.assertIn("'<NEW_LOGIN_PASSWORD>'", content)
        self.assertIn("psql postgresql://<NEW_LOGIN_ROLE>:<NEW_LOGIN_PASSWORD>@<DB_HOST>:<DB_PORT>/<DB_NAME>", content)
        self.assertIn("SELECT current_user, session_user, app.current_principal_id(), app.current_business_role();", content)


if __name__ == "__main__":
    unittest.main()
