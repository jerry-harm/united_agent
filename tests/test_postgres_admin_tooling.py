from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class PostgresAdminToolingTest(unittest.TestCase):
    def read_text(self, relative_path: str) -> str:
        return (ROOT / relative_path).read_text(encoding="utf-8")

    def assert_exists(self, relative_path: str) -> None:
        self.assertTrue((ROOT / relative_path).exists(), relative_path)

    def test_admin_skill_documents_safer_operational_policy(self) -> None:
        content = self.read_text("skills/agent-kb-postgres-admin/SKILL.md")

        self.assertIn("name: agent-kb-postgres-admin", content)
        self.assertIn("admin can create normal_user", content)
        self.assertIn("super_admin can create admin", content)
        self.assertIn("super_admin can change any global role", content)
        self.assertIn("admin does not change global roles", content)
        self.assertIn("normal_user` accounts", content)
        self.assertIn("They do not trust a user-supplied `--actor-role` flag", content)
        self.assertIn("auth.accounts", content)
        self.assertIn("auth.principal_global_roles", content)
        self.assertIn("python3 scripts/create_principal.py", content)
        self.assertIn("python3 scripts/manage_board_moderator.py assign", content)
        self.assertIn("scripts/sql/create_principal.sql", content)
        self.assertIn("compatibility:", content)
        self.assertIn("psycopg", content)
        self.assertIn('pip install "psycopg[binary]"', content)

    def test_readme_mentions_admin_skill_and_helper_scripts(self) -> None:
        content = self.read_text("README.md")

        self.assertIn("无 Web UI", content)
        self.assertIn("无应用 API", content)
        self.assertIn("部署只需要 PostgreSQL 数据库", content)
        self.assertIn("数据库本身就是系统的交付物和部署单元", content)
        self.assertIn("skills/agent-kb-postgres-admin/SKILL.md", content)
        self.assertIn("skills/agent-kb-postgres-admin/scripts/create_principal.py", content)
        self.assertIn("skills/agent-kb-postgres-admin/scripts/manage_board_moderator.py", content)
        self.assertIn("skills/agent-kb-postgres-admin/scripts/sql/create_principal.sql", content)
        self.assertIn("auth.accounts", content)
        self.assertIn("auth.principal_global_roles", content)
        self.assertIn("auth.board_moderators", content)
        self.assertIn("AGENT_KB_DB_HOST", content)
        self.assertIn("AGENT_KB_DB_USER", content)
        self.assertIn("版主管理脚本只面向已有的 `normal_user` 账号", content)
        self.assertIn("而不是来自用户在命令行上传入的角色参数", content)
        self.assertIn("psycopg", content)
        self.assertIn('pip install "psycopg[binary]"', content)
        self.assertIn("普通用户连接与身份验证", content)
        self.assertIn("不负责创建账号", content)
        self.assertIn("如果需要创建账号或管理权限，请改用 `skills/agent-kb-postgres-admin/SKILL.md`", content)

    def test_readme_includes_schema_relationship_mermaid_diagram(self) -> None:
        content = self.read_text("README.md")

        self.assertIn("```mermaid", content)
        self.assertIn("erDiagram", content)
        self.assertIn("AUTH_ACCOUNTS", content)
        self.assertIn("AUTH_PRINCIPAL_GLOBAL_ROLES", content)
        self.assertIn("AUTH_BOARD_MODERATORS", content)
        self.assertIn("APP_BOARDS", content)
        self.assertIn("APP_POSTS", content)
        self.assertIn("APP_REVIEW_ENTRIES", content)
        self.assertIn("APP_REVIEW_HISTORY", content)
        self.assertIn("APP_TAGS", content)
        self.assertIn("APP_POST_TAGS", content)

    def test_expected_python_and_sql_files_exist(self) -> None:
        self.assert_exists("scripts/_postgres_admin_common.py")
        self.assert_exists("scripts/create_principal.py")
        self.assert_exists("scripts/manage_board_moderator.py")
        self.assert_exists("scripts/sql/create_principal.sql")
        self.assert_exists("scripts/sql/manage_board_moderator_assign.sql")
        self.assert_exists("scripts/sql/manage_board_moderator_revoke.sql")
        self.assert_exists("scripts/sql/manage_board_moderator_list.sql")
        self.assert_exists("skills/agent-kb-postgres-admin/scripts/_postgres_admin_common.py")
        self.assert_exists("skills/agent-kb-postgres-admin/scripts/create_principal.py")
        self.assert_exists("skills/agent-kb-postgres-admin/scripts/manage_board_moderator.py")
        self.assert_exists("skills/agent-kb-postgres-admin/scripts/sql/create_principal.sql")
        self.assert_exists("skills/agent-kb-postgres-admin/scripts/sql/manage_board_moderator_assign.sql")
        self.assert_exists("skills/agent-kb-postgres-admin/scripts/sql/manage_board_moderator_revoke.sql")
        self.assert_exists("skills/agent-kb-postgres-admin/scripts/sql/manage_board_moderator_list.sql")

    def test_common_python_helper_uses_env_defaults(self) -> None:
        content = self.read_text("scripts/_postgres_admin_common.py")

        self.assertIn("AGENT_KB_DB_HOST", content)
        self.assertIn("AGENT_KB_DB_USER", content)
        self.assertIn("AGENT_KB_DB_PASSWORD", content)
        self.assertIn('os.environ.get("AGENT_KB_DB_PORT", "5432")', content)
        self.assertIn('os.environ.get("AGENT_KB_DB_NAME", "united_agent")', content)
        self.assertIn("import psycopg", content)
        self.assertIn("cursor.execute", content)
        self.assertIn("sql_path.read_text", content)
        self.assertIn("autocommit = False", content)

    def test_create_principal_python_script_uses_sql_file(self) -> None:
        content = self.read_text("scripts/create_principal.py")

        self.assertIn("scripts/sql/create_principal.sql", content)
        self.assertIn("--global-role", content)
        self.assertIn("AGENT_KB_NEW_PRINCIPAL_PASSWORD", content)
        self.assertIn("login role must match PostgreSQL role naming rules", content)
        self.assertIn("run_sql_file", content)

    def test_create_principal_sql_targets_account_and_grant_tables(self) -> None:
        content = self.read_text("scripts/sql/create_principal.sql")

        self.assertIn("INSERT INTO auth.accounts", content)
        self.assertIn("auth.principal_global_roles", content)
        self.assertIn("auth.create_account_login", content)
        self.assertIn("auth.current_account_id()", content)
        self.assertIn("auth.can_write()", content)
        self.assertIn("auth.is_admin()", content)
        self.assertIn("admin may create only normal_user accounts", content)

    def test_create_principal_sql_consumes_created_login_cte(self) -> None:
        content = self.read_text("scripts/sql/create_principal.sql")

        self.assertIn("created_login AS", content)
        self.assertRegex(content, r"FROM\s+created_account,\s*created_login")

    def test_board_moderator_python_script_uses_sql_files(self) -> None:
        content = self.read_text("scripts/manage_board_moderator.py")

        self.assertIn("scripts/sql/manage_board_moderator_assign.sql", content)
        self.assertIn("scripts/sql/manage_board_moderator_revoke.sql", content)
        self.assertIn("scripts/sql/manage_board_moderator_list.sql", content)
        self.assertIn("run_sql_file", content)

    def test_admin_skill_prefers_account_id_not_legacy_principal_id(self) -> None:
        content = self.read_text("skills/agent-kb-postgres-admin/SKILL.md")

        self.assertIn("--account-id 2", content)
        self.assertIn("legacy compatibility alias", content)

    def test_skill_local_python_scripts_use_skill_local_sql_files(self) -> None:
        create_principal = self.read_text("skills/agent-kb-postgres-admin/scripts/create_principal.py")
        manage_board_moderator = self.read_text("skills/agent-kb-postgres-admin/scripts/manage_board_moderator.py")

        self.assertIn('sql_file("scripts/sql/create_principal.sql")', create_principal)
        self.assertIn('sql_file("scripts/sql/manage_board_moderator_assign.sql")', manage_board_moderator)
        self.assertIn('sql_file("scripts/sql/manage_board_moderator_revoke.sql")', manage_board_moderator)
        self.assertIn('sql_file("scripts/sql/manage_board_moderator_list.sql")', manage_board_moderator)

    def test_board_moderator_sql_limits_actions_to_admin_levels(self) -> None:
        content = self.read_text("scripts/sql/manage_board_moderator_assign.sql")

        self.assertIn("auth.can_write()", content)
        self.assertIn("IF NOT auth.can_write() OR NOT auth.is_admin() THEN", content)
        self.assertIn(
            "policy violation: board moderators must be existing normal_user accounts",
            content,
        )
        self.assertIn("INSERT INTO auth.board_moderators", content)
        self.assertIn("auth.principal_global_roles", content)
        self.assertIn("role_name = 'normal_user'", content)

    def test_board_moderator_sql_supports_revoke_and_list(self) -> None:
        revoke = self.read_text("scripts/sql/manage_board_moderator_revoke.sql")
        listing = self.read_text("scripts/sql/manage_board_moderator_list.sql")

        self.assertIn("auth.can_write()", revoke)
        self.assertIn("DELETE FROM auth.board_moderators", revoke)
        self.assertIn("SELECT board_id, account_id, granted_at, granted_by", listing)
        self.assertIn("ORDER BY board_id, account_id", listing)


if __name__ == "__main__":
    unittest.main()
