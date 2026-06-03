from __future__ import annotations

import re
import unittest

from tests.live_postgres_helpers import ROOT, LivePostgresTestCase


class LiveModeratorPermissionsDocumentationTest(unittest.TestCase):
    def test_readme_documents_live_moderator_permissions_test(self) -> None:
        content = (ROOT / "docs/developer-guide.md").read_text(encoding="utf-8")

        self.assertIn("tests/test_moderator_permissions_live_flows.py", content)
        self.assertIn("uv run python -m unittest tests.test_moderator_permissions_live_flows -v", content)
        self.assertIn("python3 -m unittest tests.test_moderator_permissions_live_flows -v", content)
        self.assertIn("manage_board_moderator.py", content)


class LiveModeratorPermissionsFlowTest(LivePostgresTestCase):
    def test_manage_board_moderator_script_grants_lists_and_revokes_real_permissions(self) -> None:
        board_id = self.create_board(slug=self.make_board_slug("moderated"), title="Moderated Board")
        moderator_role = self.make_login_role("moderator")
        moderator_password = f"pw_{self.suffix}_moderator"
        author_role = self.make_login_role("author")
        author_password = f"pw_{self.suffix}_author"

        for login_role, password, display_name in (
            (moderator_role, moderator_password, "Moderator Candidate"),
            (author_role, author_password, "Post Author"),
        ):
            result = self.run_create_principal(
                actor_user="postgres",
                actor_password="postgres",
                display_name=display_name,
                global_role="normal_user",
                login_role=login_role,
                new_password=password,
            )
            self.assertEqual(result.returncode, 0, result.stderr)

        moderator_account_id = self.fetch_account_id(moderator_role)
        post_id = self.create_post(
            user=author_role,
            password=author_password,
            board_id=board_id,
            title="Moderated Post",
            body="post awaiting moderation",
        )
        review_entry_id = self.create_review_entry(
            user=author_role,
            password=author_password,
            post_id=post_id,
            conclusion="needs moderation",
        )
        with self.connection_for(user=author_role, password=author_password) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "UPDATE app.review_entries SET conclusion = %s WHERE id = %s",
                    ("edited before moderation", review_entry_id),
                )
            connection.commit()

        is_admin, is_super_admin, can_write, is_board_moderator, status = self.fetch_role_flags(
            user=moderator_role,
            password=moderator_password,
            board_id=board_id,
        )
        self.assertFalse(is_admin)
        self.assertFalse(is_super_admin)
        self.assertTrue(can_write)
        self.assertFalse(is_board_moderator)
        self.assertEqual(status, "active")

        with self.connection_for(user=moderator_role, password=moderator_password) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "UPDATE app.posts SET verification = 'verified' WHERE id = %s RETURNING verification",
                    (post_id,),
                )
                self.assertEqual(cursor.rowcount, 0)
                self.assertIsNone(cursor.fetchone())
                connection.rollback()

        assign_result = self.run_manage_board_moderator(
            "assign",
            actor_user="postgres",
            actor_password="postgres",
            board_id=board_id,
            account_id=moderator_account_id,
        )
        self.assertEqual(assign_result.returncode, 0, assign_result.stderr)

        list_result = self.run_manage_board_moderator(
            "list",
            actor_user="postgres",
            actor_password="postgres",
        )
        self.assertEqual(list_result.returncode, 0, list_result.stderr)
        self.assertRegex(list_result.stdout, rf"\b{board_id}\b\s*\|\s*\b{moderator_account_id}\b")

        is_admin, is_super_admin, can_write, is_board_moderator, status = self.fetch_role_flags(
            user=moderator_role,
            password=moderator_password,
            board_id=board_id,
        )
        self.assertFalse(is_admin)
        self.assertFalse(is_super_admin)
        self.assertTrue(can_write)
        self.assertTrue(is_board_moderator)
        self.assertEqual(status, "active")

        with self.connection_for(user=moderator_role, password=moderator_password) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "UPDATE app.posts SET verification = 'verified' WHERE id = %s RETURNING verification",
                    (post_id,),
                )
                self.assertEqual(cursor.fetchone()[0], "verified")
                cursor.execute(
                    "SELECT count(*) FROM app.review_history WHERE review_entry_id = %s",
                    (review_entry_id,),
                )
                self.assertEqual(cursor.fetchone()[0], 1)
                cursor.execute(
                    "DELETE FROM app.review_history WHERE review_entry_id = %s",
                    (review_entry_id,),
                )
                self.assertEqual(cursor.rowcount, 1)
                cursor.execute("INSERT INTO app.tags (name, created_by) VALUES (%s, auth.current_account_id()) RETURNING id", (self.make_tag_name("moderator-scope"),))
                tag_id = cursor.fetchone()[0]
                cursor.execute("INSERT INTO app.post_tags (post_id, tag_id) VALUES (%s, %s)", (post_id, tag_id))
                cursor.execute("DELETE FROM app.post_tags WHERE post_id = %s AND tag_id = %s", (post_id, tag_id))
                self.assertEqual(cursor.rowcount, 1)
                cursor.execute("DELETE FROM app.tags WHERE id = %s", (tag_id,))
                self.assertEqual(cursor.rowcount, 1)
                cursor.execute("DELETE FROM app.review_entries WHERE id = %s", (review_entry_id,))
                self.assertEqual(cursor.rowcount, 1)
                cursor.execute("DELETE FROM app.posts WHERE id = %s", (post_id,))
                self.assertEqual(cursor.rowcount, 1)
            connection.commit()

        with self.admin_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT count(*) FROM app.review_entries WHERE id = %s", (review_entry_id,))
                self.assertEqual(cursor.fetchone()[0], 0)
                cursor.execute("SELECT count(*) FROM app.posts WHERE id = %s", (post_id,))
                self.assertEqual(cursor.fetchone()[0], 0)

        revoke_result = self.run_manage_board_moderator(
            "revoke",
            actor_user="postgres",
            actor_password="postgres",
            board_id=board_id,
            account_id=moderator_account_id,
        )
        self.assertEqual(revoke_result.returncode, 0, revoke_result.stderr)

        post_after_revoke_id = self.create_post(
            user=author_role,
            password=author_password,
            board_id=board_id,
            title="Post After Revoke",
            body="post after revoke",
        )

        list_after_revoke = self.run_manage_board_moderator(
            "list",
            actor_user="postgres",
            actor_password="postgres",
        )
        self.assertEqual(list_after_revoke.returncode, 0, list_after_revoke.stderr)
        self.assertIsNone(re.search(rf"\b{board_id}\b\s*\|\s*\b{moderator_account_id}\b", list_after_revoke.stdout))

        is_admin, is_super_admin, can_write, is_board_moderator, status = self.fetch_role_flags(
            user=moderator_role,
            password=moderator_password,
            board_id=board_id,
        )
        self.assertFalse(is_board_moderator)
        self.assertTrue(can_write)
        self.assertEqual(status, "active")

        with self.connection_for(user=moderator_role, password=moderator_password) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "UPDATE app.posts SET verification = 'verified' WHERE id = %s RETURNING verification",
                    (post_after_revoke_id,),
                )
                self.assertEqual(cursor.rowcount, 0)
                self.assertIsNone(cursor.fetchone())
                connection.rollback()

    def test_non_admin_actor_cannot_manage_moderators_via_script(self) -> None:
        board_id = self.create_board(slug=self.make_board_slug("nonadmin"), title="Non Admin Board")
        actor_role = self.make_login_role("nonadmin_actor")
        actor_password = f"pw_{self.suffix}_nonadmin_actor"
        target_role = self.make_login_role("nonadmin_target")
        target_password = f"pw_{self.suffix}_nonadmin_target"

        for login_role, password, display_name in (
            (actor_role, actor_password, "Non Admin Actor"),
            (target_role, target_password, "Non Admin Target"),
        ):
            result = self.run_create_principal(
                actor_user="postgres",
                actor_password="postgres",
                display_name=display_name,
                global_role="normal_user",
                login_role=login_role,
                new_password=password,
            )
            self.assertEqual(result.returncode, 0, result.stderr)

        target_account_id = self.fetch_account_id(target_role)

        assign_result = self.run_manage_board_moderator(
            "assign",
            actor_user=actor_role,
            actor_password=actor_password,
            board_id=board_id,
            account_id=target_account_id,
        )
        self.assertNotEqual(assign_result.returncode, 0)
        self.assertIn("only admin or super_admin may manage moderators", assign_result.stderr)

        list_result = self.run_manage_board_moderator(
            "list",
            actor_user=actor_role,
            actor_password=actor_password,
        )
        self.assertNotEqual(list_result.returncode, 0)
        self.assertIn("only admin or super_admin may manage moderators", list_result.stderr)
