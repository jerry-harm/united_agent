from __future__ import annotations

import unittest

from tests.live_postgres_helpers import ROOT, LivePostgresTestCase


class LiveCategoryPostFlowDocumentationTest(unittest.TestCase):
    def test_readme_documents_live_category_post_flow_test(self) -> None:
        content = (ROOT / "docs/developer-guide.md").read_text(encoding="utf-8")

        self.assertIn("tests/test_category_post_live_flows.py", content)
        self.assertIn("uv run python -m unittest tests.test_category_post_live_flows -v", content)
        self.assertNotIn("python3 -m unittest tests.test_category_post_live_flows -v", content)
        self.assertIn("已经运行中的本地 PostgreSQL", content)
        self.assertIn("直接 SQL", content)


class LiveCategoryPostFlowTest(LivePostgresTestCase):
    def test_live_authorization_paths_match_helper_roles(self) -> None:
        category_id = self.create_category(title="Live Flow Category")
        result = self.run_create_principal(
            actor_user="postgres",
            actor_password="postgres",
            login_role=self.make_login_role("author"),
            new_password=f"pw_{self.suffix}",
            display_name="Live Flow User",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        login_role = sorted(self.created_roles)[0]
        password = f"pw_{self.suffix}"
        normal_user_account_id = self.fetch_account_id(login_role)
        post_id = self.create_post(
            user=login_role,
            password=password,
            category_id=category_id,
            title="Live Flow Post",
            body="post body from integration test",
        )

        with self.connection_for(user=login_role, password=password) as principal_connection:
            with principal_connection.cursor() as cursor:
                cursor.execute(
                    "SELECT auth.current_account_id(), auth.is_admin(), auth.is_super_admin(), auth.can_write()"
                )
                account_id, is_admin, is_super_admin, can_write = cursor.fetchone()
                self.assertEqual(account_id, normal_user_account_id)
                self.assertFalse(is_admin)
                self.assertFalse(is_super_admin)
                self.assertTrue(can_write)

                cursor.execute("SELECT id, author_id, verification FROM app.posts WHERE id = %s", (post_id,))
                post_id, author_id, verification = cursor.fetchone()
                self.assertEqual(author_id, normal_user_account_id)
                self.assertEqual(verification, "progressing")

        with self.connection_for(user=login_role, password=password) as principal_connection:
            with principal_connection.cursor() as cursor:
                with self.assertRaises(Exception) as excinfo:
                    cursor.execute(
                        """
                        INSERT INTO app.categories (slug, title, description, category_type, created_by)
                        VALUES (%s, %s, %s, 'discussion', auth.current_account_id())
                        """,
                        (self.make_category_slug("denied"), "Denied Category", "normal user should not create categories"),
                    )
                self.assertIn("row-level security", str(excinfo.exception).lower())
                principal_connection.rollback()

                with self.assertRaises(Exception) as excinfo:
                    cursor.execute(
                        """
                        INSERT INTO auth.principal_global_roles (account_id, role_name, granted_by)
                        VALUES (auth.current_account_id(), 'admin', auth.current_account_id())
                        """
                    )
                self.assertIn("row-level security", str(excinfo.exception).lower())
                principal_connection.rollback()

                cursor.execute(
                    "UPDATE app.posts SET verification = 'verified' WHERE id = %s RETURNING verification",
                    (post_id,),
                )
                self.assertEqual(cursor.rowcount, 0)
                self.assertIsNone(cursor.fetchone())
                principal_connection.rollback()

        with self.admin_connection() as admin_connection:
            with admin_connection.cursor() as cursor:
                cursor.execute(
                    "UPDATE app.posts SET verification = 'verified' WHERE id = %s RETURNING verification",
                    (post_id,),
                )
                self.assertEqual(cursor.fetchone()[0], "verified")
            admin_connection.commit()

    def test_announcement_category_is_admin_only_for_posting(self) -> None:
        login_role = self.make_login_role("announcement")
        password = f"pw_{self.suffix}_announcement"
        result = self.run_create_principal(
            actor_user="postgres",
            actor_password="postgres",
            login_role=login_role,
            new_password=password,
            display_name="Announcement Flow User",
        )
        self.assertEqual(result.returncode, 0, result.stderr)

        with self.admin_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT id FROM app.categories WHERE slug = 'hello'")
                hello_category_id = cursor.fetchone()[0]
                cursor.execute("SELECT id FROM app.categories WHERE slug = 'governance'")
                governance_category_id = cursor.fetchone()[0]
                cursor.execute("SELECT id FROM app.categories WHERE slug = 'announcement'")
                announcement_category_id = cursor.fetchone()[0]

        self.assertIsInstance(
            self.create_post(
                user=login_role,
                password=password,
                category_id=hello_category_id,
                title="Hello Category Post",
                body="ordinary user hello category post",
            ),
            int,
        )
        self.assertIsInstance(
            self.create_post(
                user=login_role,
                password=password,
                category_id=governance_category_id,
                title="Governance Category Post",
                body="ordinary user governance request",
            ),
            int,
        )

        with self.connection_for(user=login_role, password=password) as principal_connection:
            with principal_connection.cursor() as cursor:
                with self.assertRaises(Exception) as excinfo:
                    cursor.execute(
                        "SELECT app.create_post(%s, %s, %s, %s)",
                        (announcement_category_id, "announcement", "Denied Announcement", "ordinary user should be denied"),
                    )
                self.assertIn("row-level security", str(excinfo.exception).lower())
                principal_connection.rollback()

        with self.admin_connection() as admin_connection:
            with admin_connection.cursor() as cursor:
                cursor.execute(
                    "SELECT app.create_post(%s, %s, %s, %s)",
                    (announcement_category_id, "announcement", "Admin Announcement", "admin announcement post"),
                )
                post_id = cursor.fetchone()[0]
                cursor.execute("SELECT author_id FROM app.posts WHERE id = %s", (post_id,))
                author_id = cursor.fetchone()[0]
                self.assertIsInstance(post_id, int)
                cursor.execute("SELECT auth.current_account_id()")
                self.assertEqual(author_id, cursor.fetchone()[0])
            admin_connection.commit()


if __name__ == "__main__":
    unittest.main()
