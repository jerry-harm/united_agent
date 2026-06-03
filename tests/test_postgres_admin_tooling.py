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
        self.assertIn("admin` can disable `normal_user", content)
        self.assertIn("admin` can delete `normal_user", content)
        self.assertIn("super_admin` can disable `admin", content)
        self.assertIn("super_admin` can delete `admin", content)
        self.assertIn("admin does not change global roles", content)
        self.assertIn("normal_user` accounts", content)
        self.assertIn("They do not trust a user-supplied `--actor-role` flag", content)
        self.assertIn("auth.accounts", content)
        self.assertIn("auth.principal_global_roles", content)
        self.assertIn("python3 skills/agent-kb-postgres-admin/scripts/create_principal.py", content)
        self.assertIn("python3 skills/agent-kb-postgres-admin/scripts/manage_board_moderator.py assign", content)
        self.assertIn("python3 skills/agent-kb-postgres-admin/scripts/manage_account.py disable", content)
        self.assertIn("python3 skills/agent-kb-postgres-admin/scripts/manage_global_role.py grant", content)
        self.assertIn("skills/agent-kb-postgres-admin/scripts/sql/create_principal.sql", content)
        self.assertIn("run `connect` first", content)
        self.assertIn("delete reassigns posts and review/comment rows to the shared tombstone account", content)
        self.assertIn("compatibility:", content)
        self.assertIn("psycopg", content)
        self.assertIn('pip install "psycopg[binary]"', content)
        self.assertNotIn("python3 scripts/create_principal.py", content)
        self.assertNotIn("python3 scripts/manage_board_moderator.py assign", content)
        self.assertNotIn("Repo-root `scripts/` may still exist", content)

    def test_readme_mentions_admin_skill_and_helper_scripts(self) -> None:
        content = self.read_text("README.md")

        self.assertIn("以 PostgreSQL 数据库本身为核心交付物", content)
        self.assertIn("skills/agent-kb-postgres-admin/SKILL.md", content)
        self.assertIn("skills/agent-kb-postgres-admin/scripts/create_principal.py", content)
        self.assertIn("skills/agent-kb-postgres-admin/scripts/manage_board_moderator.py", content)
        self.assertIn("skills/agent-kb-postgres-admin/scripts/manage_account.py", content)
        self.assertIn("skills/agent-kb-postgres-admin/scripts/manage_global_role.py", content)
        self.assertIn("auth.accounts", content)
        self.assertIn("先运行 connect skill", content)
        self.assertIn("普通用户连接与身份验证", content)
        self.assertIn("不负责创建账号", content)
        self.assertIn("如果需要创建账号或管理权限，请改用 `skills/agent-kb-postgres-admin/SKILL.md`", content)
        self.assertIn("docs/developer-guide.md", content)

    def test_developer_guide_includes_schema_relationship_mermaid_diagram(self) -> None:
        content = self.read_text("docs/developer-guide.md")

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

    def test_developer_guide_keeps_admin_operational_detail(self) -> None:
        content = self.read_text("docs/developer-guide.md")

        self.assertIn("skills/agent-kb-postgres-admin/scripts/sql/create_principal.sql", content)
        self.assertIn("auth.principal_global_roles", content)
        self.assertIn("auth.board_moderators", content)
        self.assertIn("共享 tombstone 账号", content)
        self.assertIn("AGENT_KB_DB_HOST", content)
        self.assertIn("AGENT_KB_DB_USER", content)
        self.assertIn("版主管理脚本只面向已有的 `normal_user` 账号", content)
        self.assertIn("而不是来自用户在命令行上传入的角色参数", content)
        self.assertIn("psycopg", content)
        self.assertIn('pip install "psycopg[binary]"', content)

    def test_only_skill_bundled_admin_python_and_sql_files_exist(self) -> None:
        self.assertFalse((ROOT / "scripts/_postgres_admin_common.py").exists())
        self.assertFalse((ROOT / "scripts/create_principal.py").exists())
        self.assertFalse((ROOT / "scripts/manage_board_moderator.py").exists())
        self.assertFalse((ROOT / "scripts/sql/create_principal.sql").exists())
        self.assertFalse((ROOT / "scripts/sql/manage_board_moderator_assign.sql").exists())
        self.assertFalse((ROOT / "scripts/sql/manage_board_moderator_revoke.sql").exists())
        self.assertFalse((ROOT / "scripts/sql/manage_board_moderator_list.sql").exists())
        self.assertFalse((ROOT / "scripts/manage_account.py").exists())
        self.assertFalse((ROOT / "scripts/manage_global_role.py").exists())
        self.assert_exists("skills/agent-kb-postgres-admin/scripts/_postgres_admin_common.py")
        self.assert_exists("skills/agent-kb-postgres-admin/scripts/create_principal.py")
        self.assert_exists("skills/agent-kb-postgres-admin/scripts/manage_board_moderator.py")
        self.assert_exists("skills/agent-kb-postgres-admin/scripts/manage_account.py")
        self.assert_exists("skills/agent-kb-postgres-admin/scripts/manage_global_role.py")
        self.assert_exists("skills/agent-kb-postgres-admin/scripts/sql/create_principal.sql")
        self.assert_exists("skills/agent-kb-postgres-admin/scripts/sql/manage_board_moderator_assign.sql")
        self.assert_exists("skills/agent-kb-postgres-admin/scripts/sql/manage_board_moderator_revoke.sql")
        self.assert_exists("skills/agent-kb-postgres-admin/scripts/sql/manage_board_moderator_list.sql")
        self.assert_exists("skills/agent-kb-postgres-admin/scripts/sql/manage_account_disable.sql")
        self.assert_exists("skills/agent-kb-postgres-admin/scripts/sql/manage_account_delete.sql")
        self.assert_exists("skills/agent-kb-postgres-admin/scripts/sql/manage_global_role_grant.sql")
        self.assert_exists("skills/agent-kb-postgres-admin/scripts/sql/manage_global_role_revoke.sql")
        self.assert_exists("skills/agent-kb-postgres-admin/scripts/sql/manage_global_role_list.sql")

    def test_common_python_helper_uses_env_defaults(self) -> None:
        content = self.read_text("skills/agent-kb-postgres-admin/scripts/_postgres_admin_common.py")

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
        content = self.read_text("skills/agent-kb-postgres-admin/scripts/create_principal.py")

        self.assertIn('sql_file("scripts/sql/create_principal.sql")', content)
        self.assertIn("--global-role", content)
        self.assertIn("AGENT_KB_NEW_PRINCIPAL_PASSWORD", content)
        self.assertIn("login role must match PostgreSQL role naming rules", content)
        self.assertIn("run_sql_file", content)

    def test_create_principal_sql_targets_account_and_grant_tables(self) -> None:
        content = self.read_text("skills/agent-kb-postgres-admin/scripts/sql/create_principal.sql")

        self.assertIn("INSERT INTO auth.accounts", content)
        self.assertIn("auth.principal_global_roles", content)
        self.assertIn("auth.create_account_login", content)
        self.assertIn("auth.current_account_id()", content)
        self.assertIn("auth.can_write()", content)
        self.assertIn("auth.is_admin()", content)
        self.assertIn("admin may create only normal_user accounts", content)

    def test_create_principal_sql_consumes_created_login_cte(self) -> None:
        content = self.read_text("skills/agent-kb-postgres-admin/scripts/sql/create_principal.sql")

        self.assertIn("created_login AS", content)
        self.assertRegex(content, r"FROM\s+created_account,\s*created_login")

    def test_board_moderator_python_script_uses_sql_files(self) -> None:
        content = self.read_text("skills/agent-kb-postgres-admin/scripts/manage_board_moderator.py")

        self.assertIn('sql_file("scripts/sql/manage_board_moderator_assign.sql")', content)
        self.assertIn('sql_file("scripts/sql/manage_board_moderator_revoke.sql")', content)
        self.assertIn('sql_file("scripts/sql/manage_board_moderator_list.sql")', content)
        self.assertIn("run_sql_file", content)

    def test_manage_account_python_script_uses_sql_files(self) -> None:
        content = self.read_text("skills/agent-kb-postgres-admin/scripts/manage_account.py")

        self.assertIn('sql_file("scripts/sql/manage_account_disable.sql")', content)
        self.assertIn('sql_file("scripts/sql/manage_account_delete.sql")', content)
        self.assertIn("run_sql_file", content)

    def test_manage_global_role_python_script_uses_sql_files(self) -> None:
        content = self.read_text("skills/agent-kb-postgres-admin/scripts/manage_global_role.py")

        self.assertIn('sql_file("scripts/sql/manage_global_role_grant.sql")', content)
        self.assertIn('sql_file("scripts/sql/manage_global_role_revoke.sql")', content)
        self.assertIn('sql_file("scripts/sql/manage_global_role_list.sql")', content)
        self.assertIn("run_sql_file", content)

    def test_admin_skill_prefers_account_id_not_legacy_principal_id(self) -> None:
        content = self.read_text("skills/agent-kb-postgres-admin/SKILL.md")
        script = self.read_text("skills/agent-kb-postgres-admin/scripts/manage_board_moderator.py")

        self.assertIn("--account-id 2", content)
        self.assertNotIn("--principal-id", content)
        self.assertNotIn("--principal-id", script)

    def test_skill_local_python_scripts_use_skill_local_sql_files(self) -> None:
        create_principal = self.read_text("skills/agent-kb-postgres-admin/scripts/create_principal.py")
        manage_board_moderator = self.read_text("skills/agent-kb-postgres-admin/scripts/manage_board_moderator.py")
        manage_account = self.read_text("skills/agent-kb-postgres-admin/scripts/manage_account.py")
        manage_global_role = self.read_text("skills/agent-kb-postgres-admin/scripts/manage_global_role.py")

        self.assertIn('sql_file("scripts/sql/create_principal.sql")', create_principal)
        self.assertIn('sql_file("scripts/sql/manage_board_moderator_assign.sql")', manage_board_moderator)
        self.assertIn('sql_file("scripts/sql/manage_board_moderator_revoke.sql")', manage_board_moderator)
        self.assertIn('sql_file("scripts/sql/manage_board_moderator_list.sql")', manage_board_moderator)
        self.assertIn('sql_file("scripts/sql/manage_account_disable.sql")', manage_account)
        self.assertIn('sql_file("scripts/sql/manage_account_delete.sql")', manage_account)
        self.assertIn('sql_file("scripts/sql/manage_global_role_grant.sql")', manage_global_role)
        self.assertIn('sql_file("scripts/sql/manage_global_role_revoke.sql")', manage_global_role)
        self.assertIn('sql_file("scripts/sql/manage_global_role_list.sql")', manage_global_role)

    def test_board_moderator_sql_limits_actions_to_admin_levels(self) -> None:
        content = self.read_text("skills/agent-kb-postgres-admin/scripts/sql/manage_board_moderator_assign.sql")

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
        revoke = self.read_text("skills/agent-kb-postgres-admin/scripts/sql/manage_board_moderator_revoke.sql")
        listing = self.read_text("skills/agent-kb-postgres-admin/scripts/sql/manage_board_moderator_list.sql")

        self.assertIn("auth.can_write()", revoke)
        self.assertIn("DELETE FROM auth.board_moderators", revoke)
        self.assertIn("SELECT board_id, account_id, granted_at, granted_by", listing)
        self.assertIn("ORDER BY board_id, account_id", listing)

    def test_manage_account_sql_supports_disable_and_delete_with_tombstone_reassignment(self) -> None:
        disable_sql = self.read_text("skills/agent-kb-postgres-admin/scripts/sql/manage_account_disable.sql")
        delete_sql = self.read_text("skills/agent-kb-postgres-admin/scripts/sql/manage_account_delete.sql")
        schema_sql = self.read_text("postgres/init/001-united-agent.sql")

        self.assertIn("auth.can_manage_account(target_id)", disable_sql)
        self.assertIn("UPDATE auth.accounts", disable_sql)
        self.assertIn("account_status = 'disabled'", disable_sql)
        self.assertIn("auth.delete_managed_account", delete_sql)
        self.assertIn("CREATE FUNCTION auth.delete_managed_account", schema_sql)
        self.assertIn("auth.can_manage_account(target_id)", schema_sql)
        self.assertIn("UPDATE app.posts", schema_sql)
        self.assertIn("UPDATE app.review_entries", schema_sql)
        self.assertIn("UPDATE app.review_history", schema_sql)
        self.assertIn("DROP ROLE", schema_sql)
        self.assertIn("DELETE FROM auth.accounts", schema_sql)
        self.assertIn("deleted account tombstone", schema_sql)
        self.assertIn("deleted_account_tombstone", schema_sql)

    def test_manage_global_role_sql_supports_grant_revoke_and_list(self) -> None:
        grant_sql = self.read_text("skills/agent-kb-postgres-admin/scripts/sql/manage_global_role_grant.sql")
        revoke_sql = self.read_text("skills/agent-kb-postgres-admin/scripts/sql/manage_global_role_revoke.sql")
        list_sql = self.read_text("skills/agent-kb-postgres-admin/scripts/sql/manage_global_role_list.sql")

        self.assertIn("auth.can_write()", grant_sql)
        self.assertIn("auth.is_super_admin()", grant_sql)
        self.assertIn("INSERT INTO auth.principal_global_roles", grant_sql)
        self.assertIn("direct database maintenance for super_admin role changes", grant_sql)
        self.assertIn("auth.can_write()", revoke_sql)
        self.assertIn("auth.is_super_admin()", revoke_sql)
        self.assertIn("DELETE FROM auth.principal_global_roles", revoke_sql)
        self.assertIn("direct database maintenance for super_admin role changes", revoke_sql)
        self.assertIn("SELECT account_id, role_name::text AS role_name", list_sql)


if __name__ == "__main__":
    unittest.main()
