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
        self.assertIn('description: "Use when a user or agent already has PostgreSQL credentials', content)
        self.assertIn("compatibility:", content)
        self.assertIn("psycopg", content)
        self.assertIn('uv sync', content)
        self.assertIn('uv run python skills/agent-kb-postgres-connect/scripts/<entrypoint>', content)
        self.assertIn("base skill for ordinary-user connection, identity verification", content)
        self.assertIn("token-based registration", content)
        self.assertIn("register_with_token.py", content)
        self.assertIn("LGTM", content)
        self.assertIn("verified is a higher standard", content)
        self.assertIn("latest conclusion is the effective one", content)
        self.assertIn("token-based registration", content)
        self.assertIn("This skill does not:", content)
        self.assertIn("grant or revoke roles", content)
        self.assertIn('uv run python skills/agent-kb-postgres-connect/scripts/verify_connection.py', content)
        self.assertIn("register_with_token.py", content)
        self.assertIn("--token", content)
        self.assertIn("AGENT_KB_NEW_PASSWORD", content)
        self.assertIn('uv run python skills/agent-kb-postgres-connect/scripts/change_password.py', content)
        self.assertIn('uv run python skills/agent-kb-postgres-connect/scripts/list_content.py --list-categories', content)
        self.assertIn('uv run python skills/agent-kb-postgres-connect/scripts/upload_text_file.py', content)
        self.assertIn('uv run python skills/agent-kb-postgres-connect/scripts/read_uploaded_file.py', content)
        self.assertIn('uv run python skills/agent-kb-postgres-connect/scripts/validate_post_flow.py', content)
        self.assertIn('uv run python skills/agent-kb-postgres-connect/scripts/validate_review_flow.py', content)
        self.assertIn("<HELLO_POST_ID>", content)
        self.assertIn("--new-password-env", content)
        self.assertIn("auth.accounts", content)
        self.assertIn("united_agent", content)
        self.assertIn("connection ok", content)
        self.assertIn("run this skill first", content)
        self.assertIn("hello category", content)
        self.assertIn("low-stakes testing", content)
        self.assertIn("disposable AI chatter", content)
        self.assertIn("Use the `post_id` returned by `validate_post_flow.py` on the seeded hello category", content)
        self.assertIn("list_content.py", content)
        self.assertIn("--list-categories", content)
        self.assertIn("--announcements", content)
        self.assertIn("uv run python skills/agent-kb-postgres-connect/scripts/list_content.py --list-categories", content)
        self.assertIn("uv run python skills/agent-kb-postgres-connect/scripts/list_content.py --announcements", content)
        self.assertNotIn("validate_review_flow.py --post-id 1", content)
        self.assertNotIn("python3 - <<'PY'", content)
        self.assertNotIn("auth.create_account_login(", content)
        self.assertNotIn("python scripts/verify_connection.py", content)
    
    def test_connect_skill_bundles_local_scripts(self) -> None:
        self.assert_exists("skills/agent-kb-postgres-connect/scripts/_postgres_connect_common.py")
        self.assert_exists("skills/agent-kb-postgres-connect/scripts/verify_connection.py")
        self.assert_exists("skills/agent-kb-postgres-connect/scripts/register_with_token.py")
        self.assert_exists("skills/agent-kb-postgres-connect/scripts/change_password.py")
        self.assert_exists("skills/agent-kb-postgres-connect/scripts/upload_text_file.py")
        self.assert_exists("skills/agent-kb-postgres-connect/scripts/read_uploaded_file.py")
        self.assert_exists("skills/agent-kb-postgres-connect/scripts/validate_post_flow.py")
        self.assert_exists("skills/agent-kb-postgres-connect/scripts/validate_review_flow.py")
        self.assert_exists("skills/agent-kb-postgres-connect/scripts/list_content.py")
        self.assert_exists("skills/agent-kb-postgres-connect/scripts/sql/list_content_list_categories.sql")
        self.assert_exists("skills/agent-kb-postgres-connect/scripts/sql/list_content_announcements.sql")
        self.assert_exists("skills/agent-kb-postgres-connect/scripts/sql/upload_text_file_insert.sql")
        self.assert_exists("skills/agent-kb-postgres-connect/scripts/sql/read_uploaded_file_by_id.sql")

    def test_upload_scripts_use_shared_helper_and_uploaded_files_contract(self) -> None:
        upload_content = self.read_text("skills/agent-kb-postgres-connect/scripts/upload_text_file.py")
        read_content = self.read_text("skills/agent-kb-postgres-connect/scripts/read_uploaded_file.py")

        self.assertIn("from _postgres_connect_common import connect, render_sql", upload_content)
        self.assertIn("--file", upload_content)
        self.assertIn("--mime-type", upload_content)
        self.assertIn("app.uploaded_files", upload_content)
        self.assertIn("file_url=kb://uploaded-files/", upload_content)
        self.assertIn("from _postgres_connect_common import connect, render_sql", read_content)
        self.assertIn("--file-id", read_content)
        self.assertIn("--file-url", read_content)
        self.assertIn("app.parse_uploaded_file_url", read_content)
        self.assertIn("sql/read_uploaded_file_by_id.sql", read_content)

    def test_change_password_script_uses_shared_helper_and_explicit_password_env(self) -> None:
        content = self.read_text("skills/agent-kb-postgres-connect/scripts/change_password.py")

        self.assertIn("from _postgres_connect_common import connect, load_secret_from_env_name", content)
        self.assertIn("--new-password-env", content)
        self.assertIn("auth.change_own_password", content)
        self.assertIn("password changed", content)

    def test_register_with_token_script_uses_shared_helper_and_explicit_password_env(self) -> None:
        content = self.read_text("skills/agent-kb-postgres-connect/scripts/register_with_token.py")

        self.assertIn("from _postgres_connect_common import connect, load_secret_from_env_name", content)
        self.assertIn("--token", content)
        self.assertIn("--display-name", content)
        self.assertIn("--login-role", content)
        self.assertIn("--new-password-env", content)
        self.assertIn("auth.register_with_token", content)
        self.assertIn("registration ok", content)

    def test_connect_script_uses_skill_local_helper_and_expected_checks(self) -> None:
        content = self.read_text("skills/agent-kb-postgres-connect/scripts/verify_connection.py")

        self.assertIn("from _postgres_connect_common import connect, format_identity_row", content)
        self.assertIn("--url", content)
        self.assertIn("login resolved to no auth.accounts row", content)
        self.assertIn("is not active", content)
        self.assertIn("connection ok", content)

    def test_connect_common_helper_uses_env_defaults_and_identity_query(self) -> None:
        content = self.read_text("skills/agent-kb-postgres-connect/scripts/_postgres_connect_common.py")

        self.assertIn("AGENT_KB_DATABASE_URL", content)
        self.assertIn("import psycopg", content)

    def test_readme_mentions_connect_skill_script_and_live_test(self) -> None:
        content = self.read_text("README.md")

        self.assertIn("npx skills", content)
        self.assertIn("npx skills add jerry-harm/united_agent/skills --skill agent-kb-postgres-connect", content)
        self.assertIn("npx skills add jerry-harm/united_agent/skills --skill agent-kb-postgres-admin", content)
        self.assertIn("skills/agent-kb-postgres-connect/scripts/verify_connection.py", content)
        self.assertIn("skills/agent-kb-postgres-connect/scripts/register_with_token.py", content)
        self.assertIn("skills/agent-kb-postgres-connect/scripts/change_password.py", content)
        self.assertIn("skills/agent-kb-postgres-connect/scripts/upload_text_file.py", content)
        self.assertIn("skills/agent-kb-postgres-connect/scripts/read_uploaded_file.py", content)
        self.assertIn("skills/agent-kb-postgres-connect/scripts/validate_post_flow.py", content)
        self.assertIn("skills/agent-kb-postgres-connect/scripts/validate_review_flow.py", content)
        self.assertIn("uv run python skills/agent-kb-postgres-connect/scripts/verify_connection.py", content)
        self.assertIn("文档默认以 `AGENT_KB_DATABASE_URL` 作为连接表达方式", content)
        self.assertIn("由你自己的 agent tool 在运行时注入 `AGENT_KB_DATABASE_URL`", content)
        self.assertIn("不要把数据库密码、新账号密码写进仓库文件", content)
        self.assertIn("不要为了保存 secrets 去修改 shipped skill files", content)
        self.assertIn("普通用户连接与身份验证", content)
        self.assertIn("token 注册", content)
        self.assertIn("LGTM", content)
        self.assertIn("普通用户自助改密码", content)
        self.assertIn("文本文件上传", content)
        self.assertIn("公开读取已上传文件", content)
        self.assertIn("普通用户发帖验证", content)
        self.assertIn("普通用户评论/评审验证", content)
        self.assertIn("hello category", content)
        self.assertIn("低风险测试", content)
        self.assertIn("governance category", content)
        self.assertIn("adding tags", content)
        self.assertIn("adding categories", content)
        self.assertIn("不负责创建账号", content)
        self.assertIn("只有 `verification = 'verified'` 的 `announcement category` 公告", content)
        self.assertIn("docs/developer-guide.md", content)
        self.assertIn("docs/design-philosophy.md", content)
        self.assertNotIn("uv sync --dev", content)
        self.assertNotIn("npx skills add jerry-harm/united_agent --skill agent-kb-postgres-connect", content)
        self.assertNotIn("npx skills add jerry-harm/united_agent --skill agent-kb-postgres-admin", content)
        self.assertNotIn("python3 scripts/verify_connection.py", content)
        self.assertNotIn("tests/test_connect_skill_live_flows.py", content)
        self.assertNotIn("读取 `AGENT_KB_DATABASE_URL` 或 `AGENT_KB_*` 变量", content)

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
        self.assertIn("AGENT_KB_DATABASE_URL", readme)

    def test_developer_guide_keeps_live_test_and_env_details(self) -> None:
        content = self.read_text("docs/developer-guide.md")

        self.assertIn("governance`", content)
        self.assertIn("governance category", content)
        self.assertIn("tests/test_connect_skill_live_flows.py", content)
        self.assertIn("uv run python -m unittest tests.test_connect_skill_live_flows -v", content)
        self.assertNotIn("python3 -m unittest tests.test_connect_skill_live_flows -v", content)
        self.assertIn("pyproject.toml", content)
        self.assertIn("AGENT_KB_DATABASE_URL", content)
        self.assertIn("change_password.py --new-password-env", content)
        self.assertIn("guest/guest", content)
        self.assertIn("admin helper 现在只接受 `AGENT_KB_DATABASE_URL` 作为数据库连接入口", content)


if __name__ == "__main__":
    unittest.main()
