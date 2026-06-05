from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class PostgresUserToolingContractTest(unittest.TestCase):
    def read_text(self, relative_path: str) -> str:
        return (ROOT / relative_path).read_text(encoding="utf-8")

    def test_single_user_skill_and_two_public_scripts(self) -> None:
        self.assertTrue((ROOT / "skills/agent-kb-postgres-user/SKILL.md").exists())
        self.assertTrue((ROOT / "skills/agent-kb-postgres-user/scripts/_agent_kb_user_common.py").exists())
        self.assertTrue((ROOT / "skills/agent-kb-postgres-user/scripts/call_helper.py").exists())
        self.assertTrue((ROOT / "skills/agent-kb-postgres-user/scripts/run_sql.py").exists())
        self.assertFalse((ROOT / "skills/agent-kb-postgres-connect/SKILL.md").exists())
        self.assertFalse((ROOT / "skills/agent-kb-postgres-admin/SKILL.md").exists())
        self.assertFalse((ROOT / "skills/agent-kb-postgres-connect/scripts/sql/read_uploaded_file_by_id.sql").exists())

    def test_skill_docs_focus_on_helper_and_custom_sql_modes(self) -> None:
        content = self.read_text("skills/agent-kb-postgres-user/SKILL.md")

        self.assertIn("name: agent-kb-postgres-user", content)
        self.assertIn("helper usage", content)
        self.assertIn("custom SQL usage", content)
        self.assertIn("call_helper.py", content)
        self.assertIn("run_sql.py", content)
        self.assertIn("auth.register_with_token", content)
        self.assertIn("auth.create_account_with_login", content)
        self.assertIn("app.create_post", content)
        self.assertIn("app.create_review_entry", content)
        self.assertIn("announcement", content)
        self.assertIn("verified", content)
        self.assertIn("hello", content)
        self.assertNotIn("agent-kb-postgres-connect", content)
        self.assertNotIn("agent-kb-postgres-admin", content)
        self.assertNotIn("verify_connection.py", content)
        self.assertNotIn("create_principal.py", content)

    def test_helper_runner_is_generic_and_thin(self) -> None:
        content = self.read_text("skills/agent-kb-postgres-user/scripts/call_helper.py")
        common = self.read_text("skills/agent-kb-postgres-user/scripts/_agent_kb_user_common.py")

        self.assertIn("--helper", content)
        self.assertIn("--arg", content)
        self.assertIn("schema.function", content)
        self.assertIn("resolve_helper_arg_types", content)
        self.assertIn("SELECT * FROM {}.{}({})", content)
        self.assertIn("helper name must look like schema.function", common)
        self.assertIn("helper not found for arity", common)
        self.assertIn("AGENT_KB_DATABASE_URL", common)
        self.assertIn("import psycopg", common)
        self.assertIn("except psycopg.Error as exc", content)
        self.assertIn("fail_db_error(exc)", content)

    def test_custom_sql_runner_supports_inline_sql_and_files(self) -> None:
        content = self.read_text("skills/agent-kb-postgres-user/scripts/run_sql.py")
        common = self.read_text("skills/agent-kb-postgres-user/scripts/_agent_kb_user_common.py")

        self.assertIn("--sql", content)
        self.assertIn("--file", content)
        self.assertIn("--var", content)
        self.assertIn("provide exactly one of --sql or --file", common)
        self.assertIn("{{name}}", content)
        self.assertIn("except psycopg.Error as exc", content)
        self.assertIn("fail_db_error(exc)", content)

    def test_readme_and_developer_guide_use_single_skill_story(self) -> None:
        readme = self.read_text("README.md")
        guide = self.read_text("docs/developer-guide.md")

        self.assertIn("agent-kb-postgres-user", readme)
        self.assertIn("call_helper.py", readme)
        self.assertIn("run_sql.py", readme)
        self.assertIn("helper usage", readme)
        self.assertIn("custom SQL usage", readme)
        self.assertNotIn("agent-kb-postgres-connect", readme)
        self.assertNotIn("agent-kb-postgres-admin", readme)
        self.assertNotIn("verify_connection.py", readme)
        self.assertNotIn("create_principal.py", readme)

        self.assertIn("tests/test_postgres_user_tooling.py", guide)
        self.assertIn("tests/test_user_skill_live_flows.py", guide)
        self.assertIn("call_helper.py", guide)
        self.assertIn("run_sql.py", guide)
        self.assertNotIn("agent-kb-postgres-connect", guide)
        self.assertNotIn("agent-kb-postgres-admin", guide)


if __name__ == "__main__":
    unittest.main()
