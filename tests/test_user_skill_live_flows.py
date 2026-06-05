from __future__ import annotations

import unittest
import uuid

from psycopg import sql

from tests.live_postgres_helpers import LivePostgresTestCase, ROOT, USER_HELPER_SCRIPT, USER_SQL_SCRIPT


class LiveUserSkillDocumentationTest(unittest.TestCase):
    def test_developer_guide_documents_live_user_skill_test(self) -> None:
        content = (ROOT / "docs/developer-guide.md").read_text(encoding="utf-8")

        self.assertIn("tests/test_user_skill_live_flows.py", content)
        self.assertIn("uv run python -m unittest tests.test_user_skill_live_flows -v", content)
        self.assertIn("call_helper.py", content)
        self.assertIn("run_sql.py", content)


class LiveUserSkillTest(LivePostgresTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.login_role = self.make_login_role("user_flow")
        self.password = f"pw_{self.suffix}"
        self.unmapped_role = self.make_login_role("user_unmapped")

    def test_run_sql_reports_identity_for_mapped_active_login(self) -> None:
        created = self.run_create_principal(
            actor_user="postgres",
            actor_password="postgres",
            login_role=self.login_role,
            new_password=self.password,
            display_name="User Skill Flow",
        )
        self.assertEqual(created.returncode, 0, created.stderr)

        result = self.run_sql_script(
            "SELECT current_user, session_user, auth.current_account_id(), auth.current_account_status();",
            user=self.login_role,
            password=self.password,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("current_user", result.stdout)
        self.assertIn(self.login_role, result.stdout)
        self.assertIn("active", result.stdout)

    def test_run_sql_shows_null_identity_for_unmapped_login(self) -> None:
        with self.admin_connection(autocommit=True) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    sql.SQL("CREATE ROLE {} LOGIN PASSWORD {} ").format(
                        sql.Identifier(self.unmapped_role),
                        sql.Literal(self.password),
                    )
                )
                cursor.execute(sql.SQL("GRANT united_agent_user TO {}").format(sql.Identifier(self.unmapped_role)))
        self.created_roles.add(self.unmapped_role)

        result = self.run_sql_script(
            "SELECT current_user, session_user, auth.current_account_id(), auth.current_account_status();",
            user=self.unmapped_role,
            password=self.password,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(self.unmapped_role, result.stdout)
        self.assertNotIn("active", result.stdout)

    def test_call_helper_creates_post_for_normal_user(self) -> None:
        category_slug = f"user-skill-post-{uuid.uuid4().hex[:8]}"
        login_role = f"user_post_{uuid.uuid4().hex[:8]}"
        password = f"pw_{uuid.uuid4().hex[:8]}"
        created = self.run_create_principal(
            actor_user="postgres",
            actor_password="postgres",
            login_role=login_role,
            new_password=password,
            display_name="User Post Flow",
        )
        self.assertEqual(created.returncode, 0, created.stderr)
        category_id = self.create_category(slug=category_slug, title="User Skill Post Category")

        result = self.run_helper_script(
            "app.create_post",
            [str(category_id), "text/plain", "hello from helper", "body from helper", "json:null"],
            user=login_role,
            password=password,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("create_post", result.stdout)

    def test_call_helper_creates_review_for_normal_user(self) -> None:
        category_slug = f"user-skill-review-{uuid.uuid4().hex[:8]}"
        login_role = f"user_review_{uuid.uuid4().hex[:8]}"
        password = f"pw_{uuid.uuid4().hex[:8]}"
        created = self.run_create_principal(
            actor_user="postgres",
            actor_password="postgres",
            login_role=login_role,
            new_password=password,
            display_name="User Review Flow",
        )
        self.assertEqual(created.returncode, 0, created.stderr)
        category_id = self.create_category(slug=category_slug, title="User Skill Review Category")
        post_id = self.create_post(user=login_role, password=password, category_id=category_id, title="Review target", body="body")

        result = self.run_helper_script(
            "app.create_review_entry",
            [str(post_id), "json:false", "looks reasonable"],
            user=login_role,
            password=password,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("create_review_entry", result.stdout)


if __name__ == "__main__":
    unittest.main()
