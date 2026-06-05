from __future__ import annotations

from pathlib import Path
import subprocess
import unittest
import uuid

try:
    from psycopg import sql
except ModuleNotFoundError:  # pragma: no cover - environment-dependent
    sql = None


ROOT = Path(__file__).resolve().parents[1]
VERIFY_CONNECTION_SCRIPT = ROOT / "skills/agent-kb-postgres-connect/scripts/verify_connection.py"
VALIDATE_POST_FLOW_SCRIPT = ROOT / "skills/agent-kb-postgres-connect/scripts/validate_post_flow.py"
VALIDATE_REVIEW_FLOW_SCRIPT = ROOT / "skills/agent-kb-postgres-connect/scripts/validate_review_flow.py"

from tests.live_postgres_helpers import LivePostgresTestCase


class LiveConnectSkillDocumentationTest(unittest.TestCase):
    def test_readme_documents_live_connect_skill_test(self) -> None:
        content = (ROOT / "docs/developer-guide.md").read_text(encoding="utf-8")

        self.assertIn("tests/test_connect_skill_live_flows.py", content)
        self.assertIn("uv run python -m unittest tests.test_connect_skill_live_flows -v", content)
        self.assertNotIn("python3 -m unittest tests.test_connect_skill_live_flows -v", content)
        self.assertIn("verify_connection.py", content)
        self.assertIn("validate_post_flow.py", content)
        self.assertIn("validate_review_flow.py", content)


class LiveConnectSkillTest(LivePostgresTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.login_role = self.make_login_role("connect_flow")
        self.password = f"pw_{self.suffix}"
        self.unmapped_role = self.make_login_role("connect_unmapped")

    def run_connect_script(
        self,
        script_path: Path,
        args: list[str],
        *,
        user: str,
        password: str,
    ) -> subprocess.CompletedProcess[str]:
        return self.run_python_script(script_path, args, user=user, password=password)

    def test_bundled_connect_script_reports_successful_identity(self) -> None:
        result = self.run_create_principal(
            actor_user="postgres",
            actor_password="postgres",
            login_role=self.login_role,
            new_password=self.password,
            display_name="Connect Flow User",
        )
        self.assertEqual(result.returncode, 0, result.stderr)

        result = self.run_connect_script(
            VERIFY_CONNECTION_SCRIPT,
            [],
            user=self.login_role,
            password=self.password,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("connection ok", result.stdout)
        self.assertIn(f"pg_login_role={self.login_role}", result.stdout)
        self.assertIn("account_status=active", result.stdout)
        self.assertIn("display_name=Connect Flow User", result.stdout)

    def test_bundled_connect_script_fails_for_unmapped_login(self) -> None:
        with self.admin_connection(autocommit=True) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    sql.SQL("CREATE ROLE {} LOGIN PASSWORD {} ").format(
                        sql.Identifier(self.unmapped_role),
                        sql.Literal(self.password),
                    )
                )
                cursor.execute(sql.SQL("GRANT united_agent_user TO {}").format(sql.Identifier(self.unmapped_role)))

        result = self.run_connect_script(VERIFY_CONNECTION_SCRIPT, [], user=self.unmapped_role, password=self.password)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("login resolved to no auth.accounts row", result.stderr)

    def test_bundled_connect_script_fails_for_inactive_account(self) -> None:
        result = self.run_create_principal(
            actor_user="postgres",
            actor_password="postgres",
            login_role=self.login_role,
            new_password=self.password,
            display_name="Disabled Connect User",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        with self.admin_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "UPDATE auth.accounts SET account_status = 'disabled' WHERE pg_login_role = %s",
                    (self.login_role,),
                )
            connection.commit()

        result = self.run_connect_script(VERIFY_CONNECTION_SCRIPT, [], user=self.login_role, password=self.password)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("is not active: disabled", result.stderr)

    def test_validate_post_flow_script_reports_success_for_normal_user(self) -> None:
        category_slug = f"connect-post-{uuid.uuid4().hex[:8]}"
        login_role = f"connect_post_{uuid.uuid4().hex[:8]}"
        password = f"pw_{uuid.uuid4().hex[:8]}"
        result = self.run_create_principal(
            actor_user="postgres",
            actor_password="postgres",
            login_role=login_role,
            new_password=password,
            display_name="Connect Post User",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        category_id = self.create_category(slug=category_slug, title="Connect Post Category")

        result = self.run_connect_script(
            VALIDATE_POST_FLOW_SCRIPT,
            ["--category-id", str(category_id)],
            user=login_role,
            password=password,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("post flow ok", result.stdout)
        self.assertIn("post created", result.stdout)

    def test_validate_review_flow_script_reports_success_for_normal_user(self) -> None:
        category_slug = f"connect-review-{uuid.uuid4().hex[:8]}"
        login_role = f"connect_review_{uuid.uuid4().hex[:8]}"
        password = f"pw_{uuid.uuid4().hex[:8]}"
        result = self.run_create_principal(
            actor_user="postgres",
            actor_password="postgres",
            login_role=login_role,
            new_password=password,
            display_name="Connect Review User",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        category_id = self.create_category(slug=category_slug, title="Connect Review Category")
        post_id = self.create_post(user=login_role, password=password, category_id=category_id, title="Review target", body="body")

        result = self.run_connect_script(
            VALIDATE_REVIEW_FLOW_SCRIPT,
            ["--post-id", str(post_id)],
            user=login_role,
            password=password,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("review flow ok", result.stdout)
        self.assertIn("review entry created", result.stdout)

if __name__ == "__main__":
    unittest.main()
