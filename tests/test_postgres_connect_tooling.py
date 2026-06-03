from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class PostgresConnectToolingTest(unittest.TestCase):
    def read_text(self, relative_path: str) -> str:
        return (ROOT / relative_path).read_text(encoding="utf-8")

    def assert_exists(self, relative_path: str) -> None:
        self.assertTrue((ROOT / relative_path).exists(), relative_path)

    def test_connect_skill_documents_bundled_script_flow(self) -> None:
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
        self.assertIn("python3 skills/agent-kb-postgres-connect/scripts/verify_connection.py", content)
        self.assertIn("AGENT_KB_DB_HOST", content)
        self.assertIn("AGENT_KB_EXPECTED_LOGIN_ROLE", content)
        self.assertIn("AGENT_KB_EXPECTED_DISPLAY_NAME", content)
        self.assertIn("auth.accounts", content)
        self.assertIn("united_agent", content)
        self.assertIn("connection ok", content)
        self.assertNotIn("python3 - <<'PY'", content)
        self.assertNotIn("auth.create_account_login(", content)
        self.assertNotIn("python scripts/verify_connection.py", content)

    def test_connect_skill_bundles_local_scripts(self) -> None:
        self.assert_exists("skills/agent-kb-postgres-connect/scripts/_postgres_connect_common.py")
        self.assert_exists("skills/agent-kb-postgres-connect/scripts/verify_connection.py")

    def test_connect_script_uses_skill_local_helper_and_expected_checks(self) -> None:
        content = self.read_text("skills/agent-kb-postgres-connect/scripts/verify_connection.py")

        self.assertIn("from _postgres_connect_common import connect, format_identity_row", content)
        self.assertIn("AGENT_KB_EXPECTED_LOGIN_ROLE", content)
        self.assertIn("AGENT_KB_EXPECTED_DISPLAY_NAME", content)
        self.assertIn("login resolved to no auth.accounts row", content)
        self.assertIn("is not active", content)
        self.assertIn("expected pg_login_role", content)
        self.assertIn("expected display_name", content)
        self.assertIn("connection ok", content)

    def test_connect_common_helper_uses_env_defaults_and_identity_query(self) -> None:
        content = self.read_text("skills/agent-kb-postgres-connect/scripts/_postgres_connect_common.py")

        self.assertIn("AGENT_KB_DB_HOST", content)
        self.assertIn("AGENT_KB_DB_USER", content)
        self.assertIn("AGENT_KB_DB_PASSWORD", content)
        self.assertIn('os.environ.get("AGENT_KB_DB_PORT", "5432")', content)
        self.assertIn('os.environ.get("AGENT_KB_DB_NAME", "united_agent")', content)
        self.assertIn("import psycopg", content)
        self.assertIn("SELECT", content)
        self.assertIn("session_user", content)
        self.assertIn("auth.current_account_id()", content)
        self.assertIn("auth.current_account_status()", content)

    def test_readme_mentions_connect_skill_script_and_live_test(self) -> None:
        content = self.read_text("README.md")

        self.assertIn("skills/agent-kb-postgres-connect/scripts/verify_connection.py", content)
        self.assertIn("pyproject.toml", content)
        self.assertIn("uv sync", content)
        self.assertIn("uv run python skills/agent-kb-postgres-connect/scripts/verify_connection.py", content)
        self.assertIn("python3 skills/agent-kb-postgres-connect/scripts/verify_connection.py", content)
        self.assertIn("tests/test_connect_skill_live_flows.py", content)
        self.assertIn("uv run python -m unittest tests.test_connect_skill_live_flows -v", content)
        self.assertIn("python3 -m unittest tests.test_connect_skill_live_flows -v", content)
        self.assertIn("普通用户连接与身份验证", content)
        self.assertIn("不负责创建账号", content)
        self.assertNotIn("uv sync --dev", content)
        self.assertNotIn("python3 scripts/verify_connection.py", content)

    def test_repo_root_pyproject_supports_uv_managed_python_dependencies(self) -> None:
        self.assert_exists("pyproject.toml")

        content = self.read_text("pyproject.toml")
        readme = self.read_text("README.md")

        self.assertIn("[project]", content)
        self.assertIn('requires-python = ">=3.11"', content)
        self.assertIn("dependencies = [", content)
        self.assertIn('"psycopg[binary]",', content)
        self.assertIn("[tool.uv]", content)
        self.assertIn("package = false", content)
        self.assertNotIn("[build-system]", content)
        self.assertNotIn("[dependency-groups]", content)
        self.assertIn("uv sync", readme)
        self.assertNotIn("uv sync --dev", readme)
        self.assertIn("uv run python -m unittest tests.test_connect_skill_live_flows -v", readme)
        self.assertIn("uv run python skills/agent-kb-postgres-connect/scripts/verify_connection.py", readme)


if __name__ == "__main__":
    unittest.main()
