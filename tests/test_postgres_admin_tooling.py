import importlib.util
import os
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]


class PostgresAdminToolingTest(unittest.TestCase):
    def read_text(self, relative_path: str) -> str:
        return (ROOT / relative_path).read_text(encoding="utf-8")

    def init_sql_files(self) -> list[Path]:
        return sorted((ROOT / "postgres/init").glob("*.sql"))

    def read_init_sql(self) -> str:
        return "\n\n".join(path.read_text(encoding="utf-8") for path in self.init_sql_files())

    def assert_exists(self, relative_path: str) -> None:
        self.assertTrue((ROOT / relative_path).exists(), relative_path)

    def load_admin_common_module(self):
        module_path = ROOT / "skills/agent-kb-postgres-admin/scripts/_postgres_admin_common.py"
        spec = importlib.util.spec_from_file_location("_postgres_admin_common_test", module_path)
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        module = importlib.util.module_from_spec(spec)

        fake_psycopg = types.ModuleType("psycopg")
        fake_psycopg.connect = lambda *args, **kwargs: None
        fake_psycopg.Connection = object
        fake_psycopg.Cursor = object
        fake_psycopg_sql = types.ModuleType("psycopg.sql")
        fake_psycopg_sql.Literal = lambda value: value

        with patch.dict(
            sys.modules,
            {
                "psycopg": fake_psycopg,
                "psycopg.sql": fake_psycopg_sql,
            },
        ):
            spec.loader.exec_module(module)
        return module

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
        self.assertIn("token-based direct registration is constrained to `normal_user` only", content)
        self.assertIn("They do not trust a user-supplied `--actor-role` flag", content)
        self.assertIn("auth.accounts", content)
        self.assertIn("auth.principal_global_roles", content)
        self.assertIn('uv sync', content)
        self.assertIn('uv run python skills/agent-kb-postgres-admin/scripts/create_principal.py', content)
        self.assertIn('uv run python skills/agent-kb-postgres-admin/scripts/manage_registration_token.py create --max-uses 1', content)
        self.assertIn('uv run python skills/agent-kb-postgres-admin/scripts/manage_account.py disable', content)
        self.assertIn('uv run python skills/agent-kb-postgres-admin/scripts/manage_account.py reset-password --account-id 2 --new-password-env AGENT_KB_TARGET_PASSWORD', content)
        self.assertIn('uv run python skills/agent-kb-postgres-admin/scripts/manage_global_role.py grant', content)
        self.assertIn("skills/agent-kb-postgres-admin/scripts/sql/create_principal.sql", content)
        self.assertIn("run `connect` first", content)
        self.assertIn("Bootstrap identity", content)
        self.assertIn("postgres/init/006-bootstrap-and-seed.sql", content)
        self.assertIn("create the first `super_admin`", content)
        self.assertIn("os.environ", content)
        self.assertIn("do not edit shipped skill files to store secrets", content)
        self.assertIn("typically as `AGENT_KB_DATABASE_URL`", content)
        self.assertIn("Admin connection contract: shipped admin helpers require `AGENT_KB_DATABASE_URL`", content)
        self.assertIn("prefer explicit env-variable-name flags such as `--new-password-env`", content)
        self.assertIn("AGENT_KB_NEW_PRINCIPAL_PASSWORD", content)
        self.assertIn("The database connection itself still comes from `AGENT_KB_DATABASE_URL`", content)
        self.assertIn("No fixed password env fallback exists for reset-password", content)
        self.assertIn("Only `admin` and `super_admin` may create registration tokens", content)
        self.assertIn("token-based direct registration", content)
        self.assertIn("single-use or shared multi-use token", content)
        self.assertIn("optional expiration timestamp", content)
        self.assertIn("not mapped to `auth.accounts`", content)
        self.assertIn("delete reassigns posts and review/comment rows to the shared tombstone account", content)
        self.assertIn("compatibility:", content)
        self.assertIn("psycopg", content)
        self.assertIn('uv run python skills/agent-kb-postgres-admin/scripts/<entrypoint>', content)
        self.assertNotIn("python3 scripts/create_principal.py", content)
        self.assertIn("announcement approval", content)
        self.assertIn("admin-only moderation", content)
        self.assertNotIn("Repo-root `scripts/` may still exist", content)
        self.assertNotIn("AGENT_KB_DB_HOST", content)

    def test_readme_mentions_admin_skill_and_helper_scripts(self) -> None:
        content = self.read_text("README.md")

        self.assertIn("以 PostgreSQL 数据库本身为核心交付物", content)
        self.assertIn("npx skills add jerry-harm/united_agent/skills --skill agent-kb-postgres-connect", content)
        self.assertIn("npx skills add jerry-harm/united_agent/skills --skill agent-kb-postgres-admin", content)
        self.assertIn("skills/agent-kb-postgres-admin/SKILL.md", content)
        self.assertIn("skills/agent-kb-postgres-admin/scripts/create_principal.py", content)
        self.assertIn("skills/agent-kb-postgres-admin/scripts/manage_registration_token.py", content)
        self.assertIn("skills/agent-kb-postgres-admin/scripts/manage_account.py", content)
        self.assertIn("skills/agent-kb-postgres-admin/scripts/manage_global_role.py", content)
        self.assertIn("auth.accounts", content)
        self.assertIn("`postgres/init/*.sql` 会按文件名顺序初始化数据库", content)
        self.assertIn("`postgres/init/006-bootstrap-and-seed.sql` 会把本地 `postgres` 登录写入 `auth.accounts`，并授予它 `super_admin`", content)
        self.assertIn("`create_principal.py` **不能**创建 `super_admin`", content)
        self.assertIn("bootstrap identity 与后续普通运维账号是两件事", content)
        self.assertIn("优先在运行时通过 `--new-password` 传入", content)
        self.assertIn("--new-password-env", content)
        self.assertIn("helper 也兼容一个历史密码环境变量", content)
        self.assertIn("先运行 connect skill", content)
        self.assertIn("普通用户连接与身份验证", content)
        self.assertIn("不负责创建账号", content)
        self.assertIn("如果需要创建账号或管理权限，请改用 `skills/agent-kb-postgres-admin/SKILL.md`", content)
        self.assertIn("docs/developer-guide.md", content)
        self.assertNotIn("npx skills add jerry-harm/united_agent --skill agent-kb-postgres-connect", content)
        self.assertNotIn("npx skills add jerry-harm/united_agent --skill agent-kb-postgres-admin", content)
        self.assertNotIn("--global-role super_admin", content)
        self.assertNotIn("AGENT_KB_DB_HOST", content)

    def test_developer_guide_includes_schema_relationship_mermaid_diagram(self) -> None:
        content = self.read_text("docs/developer-guide.md")

        self.assertIn("```mermaid", content)
        self.assertIn("erDiagram", content)
        self.assertIn("AUTH_ACCOUNTS", content)
        self.assertIn("APP_PROFILES", content)
        self.assertIn("AUTH_PRINCIPAL_GLOBAL_ROLES", content)
        self.assertIn("APP_CATEGORIES", content)
        self.assertIn("APP_POSTS", content)
        self.assertIn("APP_FILE_BLOBS", content)
        self.assertIn("APP_POST_ATTACHMENTS", content)
        self.assertIn("APP_REVIEW_ENTRIES", content)
        self.assertIn("APP_REVIEW_ENTRY_ATTACHMENTS", content)
        self.assertIn("APP_REVIEW_HISTORY", content)
        self.assertIn("APP_TAGS", content)
        self.assertIn("APP_POST_TAGS", content)

    def test_developer_guide_keeps_admin_operational_detail(self) -> None:
        content = self.read_text("docs/developer-guide.md")

        self.assertIn("skills/agent-kb-postgres-admin/scripts/sql/create_principal.sql", content)
        self.assertIn("auth.principal_global_roles", content)
        self.assertIn("APP_CATEGORIES", content)
        self.assertIn("共享 tombstone 账号", content)
        self.assertIn("AGENT_KB_DATABASE_URL", content)
        self.assertIn("admin helper 现在只接受 `AGENT_KB_DATABASE_URL`", content)
        self.assertIn("管理员负责公告审批、内容删除、标签维护等高权限内容管理", content)
        self.assertIn("而不是来自用户在命令行上传入的角色参数", content)
        self.assertIn("psycopg", content)
        self.assertIn('uv sync', content)

    def test_only_skill_bundled_admin_python_and_sql_files_exist(self) -> None:
        self.assertFalse((ROOT / "scripts/_postgres_admin_common.py").exists())
        self.assertFalse((ROOT / "scripts/create_principal.py").exists())
        self.assertFalse((ROOT / "scripts/manage_registration_token.py").exists())
        self.assertFalse((ROOT / "scripts/sql/create_principal.sql").exists())
        self.assertFalse((ROOT / "scripts/manage_account.py").exists())
        self.assertFalse((ROOT / "scripts/manage_global_role.py").exists())
        self.assert_exists("skills/agent-kb-postgres-admin/scripts/_postgres_admin_common.py")
        self.assert_exists("skills/agent-kb-postgres-admin/scripts/create_principal.py")
        self.assert_exists("skills/agent-kb-postgres-admin/scripts/manage_registration_token.py")
        self.assert_exists("skills/agent-kb-postgres-admin/scripts/manage_account.py")
        self.assert_exists("skills/agent-kb-postgres-admin/scripts/manage_global_role.py")
        self.assert_exists("skills/agent-kb-postgres-admin/scripts/sql/create_principal.sql")
        self.assert_exists("skills/agent-kb-postgres-admin/scripts/sql/manage_account_disable.sql")
        self.assert_exists("skills/agent-kb-postgres-admin/scripts/sql/manage_account_delete.sql")
        self.assert_exists("skills/agent-kb-postgres-admin/scripts/sql/manage_account_reset_password.sql")
        self.assert_exists("skills/agent-kb-postgres-admin/scripts/sql/manage_global_role_grant.sql")
        self.assert_exists("skills/agent-kb-postgres-admin/scripts/sql/manage_global_role_revoke.sql")
        self.assert_exists("skills/agent-kb-postgres-admin/scripts/sql/manage_global_role_list.sql")
        self.assertFalse((ROOT / ".agents/skills/agent-kb-postgres-admin").exists())
        self.assertFalse((ROOT / ".agents/skills/agent-kb-postgres-connect").exists())

    def test_common_python_helper_uses_database_url(self) -> None:
        content = self.read_text("skills/agent-kb-postgres-admin/scripts/_postgres_admin_common.py")

        self.assertIn('require_env("AGENT_KB_DATABASE_URL")', content)
        self.assertIn("psycopg.connect(database_url())", content)
        self.assertIn("import psycopg", content)
        self.assertIn("cursor.execute", content)
        self.assertIn("sql_path.read_text", content)
        self.assertIn("autocommit = False", content)
        self.assertNotIn("AGENT_KB_DB_HOST", content)

    def test_common_python_helper_fails_fast_without_database_url(self) -> None:
        module = self.load_admin_common_module()

        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(SystemExit) as context:
                module.database_url()

        self.assertEqual(
            str(context.exception),
            "missing required environment variable: AGENT_KB_DATABASE_URL",
        )

    def test_open_connection_uses_database_url_conninfo(self) -> None:
        module = self.load_admin_common_module()

        with patch.dict(os.environ, {"AGENT_KB_DATABASE_URL": "postgres://example"}, clear=True):
            with patch.object(module.psycopg, "connect") as connect:
                module.open_connection()

        connect.assert_called_once_with("postgres://example")

    def test_create_principal_python_script_uses_sql_file(self) -> None:
        content = self.read_text("skills/agent-kb-postgres-admin/scripts/create_principal.py")

        self.assertIn('sql_file("scripts/sql/create_principal.sql")', content)
        self.assertIn("--global-role", content)
        self.assertIn("AGENT_KB_NEW_PRINCIPAL_PASSWORD", content)
        self.assertIn("login role must match PostgreSQL role naming rules", content)
        self.assertIn("run_sql_file", content)

    def test_admin_schema_exposes_canonical_account_management_functions(self) -> None:
        content = self.read_text("postgres/init/003-auth-functions.sql")

        self.assertIn("CREATE FUNCTION auth.create_account_with_login(", content)
        self.assertIn("CREATE FUNCTION auth.disable_managed_account(", content)
        self.assertIn("CREATE FUNCTION auth.grant_global_role(", content)
        self.assertIn("CREATE FUNCTION auth.revoke_global_role(", content)

    def test_create_principal_sql_targets_account_and_grant_tables(self) -> None:
        content = self.read_text("skills/agent-kb-postgres-admin/scripts/sql/create_principal.sql")

        self.assertIn("FROM auth.create_account_with_login(", content)
        self.assertIn("{{principal_type}}::auth.principal_type", content)
        self.assertIn("{{global_role}}::auth.global_role", content)
        self.assertNotIn("INSERT INTO auth.accounts", content)
        self.assertNotIn("INSERT INTO auth.principal_global_roles", content)
        self.assertNotIn("auth.create_account_login(", content)

    def test_create_principal_sql_is_thin_function_delegation(self) -> None:
        content = self.read_text("skills/agent-kb-postgres-admin/scripts/sql/create_principal.sql")

        self.assertNotIn("DO $$", content)
        self.assertNotIn("created_login AS", content)
        self.assertNotIn("created_account AS", content)

    def test_manage_account_python_script_uses_sql_files(self) -> None:
        content = self.read_text("skills/agent-kb-postgres-admin/scripts/manage_account.py")

        self.assertIn('sql_file("scripts/sql/manage_account_disable.sql")', content)
        self.assertIn('sql_file("scripts/sql/manage_account_delete.sql")', content)
        self.assertIn('sql_file("scripts/sql/manage_account_reset_password.sql")', content)
        self.assertIn("--new-password-env", content)
        self.assertIn("load_secret_from_env_name", content)
        self.assertIn("run_sql_file", content)

    def test_manage_global_role_python_script_uses_sql_files(self) -> None:
        content = self.read_text("skills/agent-kb-postgres-admin/scripts/manage_global_role.py")

        self.assertIn('sql_file("scripts/sql/manage_global_role_grant.sql")', content)
        self.assertIn('sql_file("scripts/sql/manage_global_role_revoke.sql")', content)
        self.assertIn('sql_file("scripts/sql/manage_global_role_list.sql")', content)
        self.assertIn("run_sql_file", content)

    def test_manage_registration_token_python_script_uses_sql_files_and_secret_generation(self) -> None:
        content = self.read_text("skills/agent-kb-postgres-admin/scripts/manage_registration_token.py")

        self.assertIn('sql_file("scripts/sql/manage_registration_token_create.sql")', content)
        self.assertIn('sql_file("scripts/sql/manage_registration_token_list.sql")', content)
        self.assertIn('sql_file("scripts/sql/manage_registration_token_revoke.sql")', content)
        self.assertIn("secrets.token_urlsafe", content)
        self.assertIn("--max-uses", content)
        self.assertIn("--expires-at", content)
        self.assertIn("run_sql_file", content)

    def test_manage_registration_token_sql_enforces_admin_creation_and_listing(self) -> None:
        create_sql = self.read_text("skills/agent-kb-postgres-admin/scripts/sql/manage_registration_token_create.sql")
        list_sql = self.read_text("skills/agent-kb-postgres-admin/scripts/sql/manage_registration_token_list.sql")
        revoke_sql = self.read_text("skills/agent-kb-postgres-admin/scripts/sql/manage_registration_token_revoke.sql")

        self.assertIn("auth.issue_registration_token", create_sql)
        self.assertIn("auth.can_write()", create_sql)
        self.assertIn("auth.is_admin()", create_sql)
        self.assertIn("SELECT id, token", create_sql)
        self.assertIn("FROM auth.registration_tokens", list_sql)
        self.assertIn("ORDER BY created_at DESC, id DESC", list_sql)
        self.assertIn("UPDATE auth.registration_tokens", revoke_sql)
        self.assertIn("revoked_at = now()", revoke_sql)

    def test_admin_skill_prefers_account_id_not_legacy_principal_id(self) -> None:
        content = self.read_text("skills/agent-kb-postgres-admin/SKILL.md")

        self.assertIn("--account-id 2", content)
        self.assertNotIn("--principal-id", content)
        self.assertNotIn("--principal-id", self.read_text("skills/agent-kb-postgres-admin/scripts/manage_account.py"))

    def test_skill_local_python_scripts_use_skill_local_sql_files(self) -> None:
        create_principal = self.read_text("skills/agent-kb-postgres-admin/scripts/create_principal.py")
        manage_account = self.read_text("skills/agent-kb-postgres-admin/scripts/manage_account.py")
        manage_global_role = self.read_text("skills/agent-kb-postgres-admin/scripts/manage_global_role.py")

        self.assertIn('sql_file("scripts/sql/create_principal.sql")', create_principal)
        self.assertIn('sql_file("scripts/sql/manage_account_disable.sql")', manage_account)
        self.assertIn('sql_file("scripts/sql/manage_account_delete.sql")', manage_account)
        self.assertIn('sql_file("scripts/sql/manage_account_reset_password.sql")', manage_account)
        self.assertIn('sql_file("scripts/sql/manage_global_role_grant.sql")', manage_global_role)
        self.assertIn('sql_file("scripts/sql/manage_global_role_revoke.sql")', manage_global_role)
        self.assertIn('sql_file("scripts/sql/manage_global_role_list.sql")', manage_global_role)

    def test_manage_account_sql_supports_disable_and_delete_with_tombstone_reassignment(self) -> None:
        disable_sql = self.read_text("skills/agent-kb-postgres-admin/scripts/sql/manage_account_disable.sql")
        delete_sql = self.read_text("skills/agent-kb-postgres-admin/scripts/sql/manage_account_delete.sql")
        reset_sql = self.read_text("skills/agent-kb-postgres-admin/scripts/sql/manage_account_reset_password.sql")
        schema_sql = self.read_init_sql()

        self.assertIn("auth.disable_managed_account", disable_sql)
        self.assertNotIn("UPDATE auth.accounts", disable_sql)
        self.assertNotIn("auth.can_manage_account(target_id)", disable_sql)
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
        self.assertIn("auth.reset_managed_account_password", reset_sql)
        self.assertIn("auth.reset_managed_account_password", schema_sql)
        self.assertIn("auth.can_manage_account(target_id)", schema_sql)
        self.assertIn("ALTER ROLE %I PASSWORD %L", schema_sql)

    def test_manage_global_role_sql_supports_grant_revoke_and_list(self) -> None:
        grant_sql = self.read_text("skills/agent-kb-postgres-admin/scripts/sql/manage_global_role_grant.sql")
        revoke_sql = self.read_text("skills/agent-kb-postgres-admin/scripts/sql/manage_global_role_revoke.sql")
        list_sql = self.read_text("skills/agent-kb-postgres-admin/scripts/sql/manage_global_role_list.sql")

        self.assertIn("auth.grant_global_role", grant_sql)
        self.assertNotIn("INSERT INTO auth.principal_global_roles", grant_sql)
        self.assertNotIn("DO $$", grant_sql)
        self.assertIn("auth.revoke_global_role", revoke_sql)
        self.assertNotIn("DELETE FROM auth.principal_global_roles", revoke_sql)
        self.assertNotIn("DO $$", revoke_sql)
        self.assertIn("SELECT account_id, role_name::text AS role_name", list_sql)


if __name__ == "__main__":
    unittest.main()
