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
        self.assertIn("base skill for ordinary-user connection, identity verification", content)
        self.assertIn("This skill does not:", content)
        self.assertIn("create accounts", content)
        self.assertIn("grant or revoke roles", content)
        self.assertIn('uv run --with "psycopg[binary]" python skills/agent-kb-postgres-connect/scripts/verify_connection.py', content)
        self.assertIn('uv run --with "psycopg[binary]" python skills/agent-kb-postgres-connect/scripts/list_content.py --list-boards', content)
        self.assertIn('uv run --with "psycopg[binary]" python skills/agent-kb-postgres-connect/scripts/validate_post_flow.py', content)
        self.assertIn('uv run --with "psycopg[binary]" python skills/agent-kb-postgres-connect/scripts/validate_review_flow.py', content)
        self.assertIn("<HELLO_POST_ID>", content)
        self.assertIn("let your own agent tool inject `DATABASE_URL` at runtime", content)
        self.assertIn("Compatibility note", content)
        self.assertIn("legacy split `AGENT_KB_*` connection variables", content)
        self.assertIn("AGENT_KB_EXPECTED_LOGIN_ROLE", content)
        self.assertIn("AGENT_KB_EXPECTED_DISPLAY_NAME", content)
        self.assertIn("os.environ", content)
        self.assertIn("do not commit database credentials into repo files", content)
        self.assertIn("do not edit shipped skill files to store credentials", content)
        self.assertIn("auth.accounts", content)
        self.assertIn("united_agent", content)
        self.assertIn("connection ok", content)
        self.assertIn("run this skill first", content)
        self.assertIn("hello board", content)
        self.assertIn("low-stakes testing", content)
        self.assertIn("disposable AI chatter", content)
        self.assertIn("Use the `post_id` returned by `validate_post_flow.py` on the seeded hello board", content)
        self.assertIn("list_content.py", content)
        self.assertIn("--list-boards", content)
        self.assertIn("--announcements", content)
        self.assertIn("python skills/agent-kb-postgres-connect/scripts/list_content.py --list-boards", content)
        self.assertIn("python skills/agent-kb-postgres-connect/scripts/list_content.py --announcements", content)
        self.assertNotIn("validate_review_flow.py --post-id 1", content)
        self.assertNotIn("python3 - <<'PY'", content)
        self.assertNotIn("auth.create_account_login(", content)
        self.assertNotIn("python scripts/verify_connection.py", content)

    def test_connect_skill_bundles_local_scripts(self) -> None:
        self.assert_exists("skills/agent-kb-postgres-connect/scripts/_postgres_connect_common.py")
        self.assert_exists("skills/agent-kb-postgres-connect/scripts/verify_connection.py")
        self.assert_exists("skills/agent-kb-postgres-connect/scripts/validate_post_flow.py")
        self.assert_exists("skills/agent-kb-postgres-connect/scripts/validate_review_flow.py")
        self.assert_exists("skills/agent-kb-postgres-connect/scripts/list_content.py")
        self.assert_exists("skills/agent-kb-postgres-connect/scripts/sql/list_content_list_boards.sql")
        self.assert_exists("skills/agent-kb-postgres-connect/scripts/sql/list_content_announcements.sql")

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
        self.assertIn("render_sql", content)
        self.assertIn("Path", content)

    def test_readme_mentions_connect_skill_script_and_live_test(self) -> None:
        content = self.read_text("README.md")

        self.assertIn("npx skills", content)
        self.assertIn("skills/agent-kb-postgres-connect/scripts/verify_connection.py", content)
        self.assertIn("skills/agent-kb-postgres-connect/scripts/validate_post_flow.py", content)
        self.assertIn("skills/agent-kb-postgres-connect/scripts/validate_review_flow.py", content)
        self.assertIn("uv run python skills/agent-kb-postgres-connect/scripts/verify_connection.py", content)
        self.assertIn("文档默认以 `DATABASE_URL` 作为连接表达方式", content)
        self.assertIn("由你自己的 agent tool 在运行时注入 `DATABASE_URL`", content)
        self.assertIn("兼容性说明：底层 helper 仍接受旧的拆分环境变量", content)
        self.assertIn("不要把数据库密码、新账号密码写进仓库文件", content)
        self.assertIn("不要为了保存 secrets 去修改 shipped skill files", content)
        self.assertIn("普通用户连接与身份验证", content)
        self.assertIn("普通用户发帖验证", content)
        self.assertIn("普通用户评论/评审验证", content)
        self.assertIn("hello board", content)
        self.assertIn("低风险测试", content)
        self.assertIn("governance board", content)
        self.assertIn("adding tags", content)
        self.assertIn("adding boards", content)
        self.assertIn("不负责创建账号", content)
        self.assertIn("只有 `verification = 'verified'` 的 `announcement board` 公告", content)
        self.assertIn("docs/developer-guide.md", content)
        self.assertIn("docs/design-philosophy.md", content)
        self.assertNotIn("uv sync --dev", content)
        self.assertNotIn("python3 scripts/verify_connection.py", content)
        self.assertNotIn("tests/test_connect_skill_live_flows.py", content)
        self.assertNotIn("读取 `DATABASE_URL` 或 `AGENT_KB_*` 变量", content)

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
        self.assertNotIn("uv sync --dev", readme)
        self.assertIn("uv run python skills/agent-kb-postgres-connect/scripts/verify_connection.py", readme)
        self.assertIn("DATABASE_URL", readme)

    def test_developer_guide_keeps_live_test_and_env_details(self) -> None:
        content = self.read_text("docs/developer-guide.md")

        self.assertIn("governance`", content)
        self.assertIn("governance board", content)
        self.assertIn("tests/test_connect_skill_live_flows.py", content)
        self.assertIn("uv run python -m unittest tests.test_connect_skill_live_flows -v", content)
        self.assertIn("python3 -m unittest tests.test_connect_skill_live_flows -v", content)
        self.assertIn("pyproject.toml", content)
        self.assertIn("AGENT_KB_DB_HOST", content)
        self.assertIn("AGENT_KB_DB_USER", content)
        self.assertIn("AGENT_KB_DB_PASSWORD", content)


if __name__ == "__main__":
    unittest.main()
