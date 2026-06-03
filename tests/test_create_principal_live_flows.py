from __future__ import annotations

import unittest

from tests.live_postgres_helpers import ROOT, LivePostgresTestCase


class LiveCreatePrincipalDocumentationTest(unittest.TestCase):
    def test_readme_documents_live_create_principal_flow_test(self) -> None:
        content = (ROOT / "docs/developer-guide.md").read_text(encoding="utf-8")

        self.assertIn("tests/test_create_principal_live_flows.py", content)
        self.assertIn("uv run python -m unittest tests.test_create_principal_live_flows -v", content)
        self.assertIn("python3 -m unittest tests.test_create_principal_live_flows -v", content)
        self.assertIn("create_principal.py", content)
        self.assertIn("manage_account.py", content)
        self.assertIn("manage_global_role.py", content)


class LiveCreatePrincipalFlowTest(LivePostgresTestCase):
    def test_live_create_principal_authorization_matrix(self) -> None:
        admin_role = self.make_login_role("admin")
        admin_password = f"pw_{self.suffix}_admin"
        normal_actor_role = self.make_login_role("normal")
        normal_actor_password = f"pw_{self.suffix}_normal"
        created_by_admin_role = self.make_login_role("child")
        created_by_admin_password = f"pw_{self.suffix}_child"
        denied_admin_role = self.make_login_role("denied_admin")

        admin_result = self.run_create_principal(
            actor_user="postgres",
            actor_password="postgres",
            display_name="Live Admin Actor",
            global_role="admin",
            login_role=admin_role,
            new_password=admin_password,
        )
        self.assertEqual(admin_result.returncode, 0, admin_result.stderr)

        normal_actor_result = self.run_create_principal(
            actor_user="postgres",
            actor_password="postgres",
            display_name="Live Normal Actor",
            global_role="normal_user",
            login_role=normal_actor_role,
            new_password=normal_actor_password,
        )
        self.assertEqual(normal_actor_result.returncode, 0, normal_actor_result.stderr)

        created_by_admin_result = self.run_create_principal(
            actor_user=admin_role,
            actor_password=admin_password,
            display_name="Created By Admin",
            global_role="normal_user",
            login_role=created_by_admin_role,
            new_password=created_by_admin_password,
        )
        self.assertEqual(created_by_admin_result.returncode, 0, created_by_admin_result.stderr)

        denied_admin_result = self.run_create_principal(
            actor_user=admin_role,
            actor_password=admin_password,
            display_name="Denied Admin Creation",
            global_role="admin",
            login_role=denied_admin_role,
            new_password=f"pw_{self.suffix}_denied",
        )
        self.assertNotEqual(denied_admin_result.returncode, 0)
        self.assertIn("admin may create only normal_user accounts", denied_admin_result.stderr)

        denied_by_normal_result = self.run_create_principal(
            actor_user=normal_actor_role,
            actor_password=normal_actor_password,
            display_name="Denied Normal Creation",
            global_role="normal_user",
            login_role=self.make_login_role("normal_denied"),
            new_password=f"pw_{self.suffix}_normal_denied",
        )
        self.assertNotEqual(denied_by_normal_result.returncode, 0)
        self.assertIn("only admin or super_admin may create accounts", denied_by_normal_result.stderr)

        is_admin, is_super_admin, can_write, _, status = self.fetch_role_flags(user=admin_role, password=admin_password)
        self.assertTrue(is_admin)
        self.assertFalse(is_super_admin)
        self.assertTrue(can_write)
        self.assertEqual(status, "active")

        is_admin, is_super_admin, can_write, _, status = self.fetch_role_flags(
            user=normal_actor_role,
            password=normal_actor_password,
        )
        self.assertFalse(is_admin)
        self.assertFalse(is_super_admin)
        self.assertTrue(can_write)
        self.assertEqual(status, "active")

    def test_disabled_admin_still_reads_as_admin_but_cannot_create_accounts(self) -> None:
        admin_role = self.make_login_role("disabled_admin")
        admin_password = f"pw_{self.suffix}_disabled_admin"

        create_admin = self.run_create_principal(
            actor_user="postgres",
            actor_password="postgres",
            display_name="Disabled Admin Actor",
            global_role="admin",
            login_role=admin_role,
            new_password=admin_password,
        )
        self.assertEqual(create_admin.returncode, 0, create_admin.stderr)

        self.set_account_status(admin_role, "disabled")

        is_admin, is_super_admin, can_write, _, status = self.fetch_role_flags(user=admin_role, password=admin_password)
        self.assertTrue(is_admin)
        self.assertFalse(is_super_admin)
        self.assertFalse(can_write)
        self.assertEqual(status, "disabled")

        denied_result = self.run_create_principal(
            actor_user=admin_role,
            actor_password=admin_password,
            display_name="Denied Disabled Admin Creation",
            global_role="normal_user",
            login_role=self.make_login_role("disabled_denied"),
            new_password=f"pw_{self.suffix}_disabled_denied",
        )
        self.assertNotEqual(denied_result.returncode, 0)
        self.assertIn("only admin or super_admin may create accounts", denied_result.stderr)

    def test_super_admin_can_grant_and_revoke_global_roles_via_script(self) -> None:
        target_role = self.make_login_role("global_role_target")
        target_password = f"pw_{self.suffix}_global_role_target"
        admin_role = self.make_login_role("global_role_admin")
        admin_password = f"pw_{self.suffix}_global_role_admin"

        create_admin = self.run_create_principal(
            actor_user="postgres",
            actor_password="postgres",
            display_name="Global Role Admin",
            global_role="admin",
            login_role=admin_role,
            new_password=admin_password,
        )
        self.assertEqual(create_admin.returncode, 0, create_admin.stderr)

        create_target = self.run_create_principal(
            actor_user="postgres",
            actor_password="postgres",
            display_name="Global Role Target",
            global_role="normal_user",
            login_role=target_role,
            new_password=target_password,
        )
        self.assertEqual(create_target.returncode, 0, create_target.stderr)

        account_id = self.fetch_account_id(target_role)

        grant_result = self.run_manage_global_role(
            "grant",
            actor_user="postgres",
            actor_password="postgres",
            account_id=account_id,
            role_name="admin",
        )
        self.assertEqual(grant_result.returncode, 0, grant_result.stderr)

        denied_admin_grant = self.run_manage_global_role(
            "grant",
            actor_user=admin_role,
            actor_password=admin_password,
            account_id=account_id,
            role_name="admin",
        )
        self.assertNotEqual(denied_admin_grant.returncode, 0)
        self.assertIn("only active super_admin may grant global roles", denied_admin_grant.stderr)

        is_admin, is_super_admin, can_write, _, status = self.fetch_role_flags(user=target_role, password=target_password)
        self.assertTrue(is_admin)
        self.assertFalse(is_super_admin)
        self.assertTrue(can_write)
        self.assertEqual(status, "active")

        revoke_result = self.run_manage_global_role(
            "revoke",
            actor_user="postgres",
            actor_password="postgres",
            account_id=account_id,
            role_name="admin",
        )
        self.assertEqual(revoke_result.returncode, 0, revoke_result.stderr)

        is_admin, is_super_admin, can_write, _, status = self.fetch_role_flags(user=target_role, password=target_password)
        self.assertFalse(is_admin)
        self.assertFalse(is_super_admin)
        self.assertTrue(can_write)
        self.assertEqual(status, "active")

    def test_manage_account_permissions_follow_admin_and_super_admin_boundaries(self) -> None:
        admin_role = self.make_login_role("account_admin")
        admin_password = f"pw_{self.suffix}_account_admin"
        target_role = self.make_login_role("delete_target")
        target_password = f"pw_{self.suffix}_delete_target"
        second_admin_role = self.make_login_role("other_admin")
        second_admin_password = f"pw_{self.suffix}_other_admin"

        create_admin = self.run_create_principal(
            actor_user="postgres",
            actor_password="postgres",
            display_name="Account Admin",
            global_role="admin",
            login_role=admin_role,
            new_password=admin_password,
        )
        self.assertEqual(create_admin.returncode, 0, create_admin.stderr)

        create_target = self.run_create_principal(
            actor_user=admin_role,
            actor_password=admin_password,
            display_name="Delete Target",
            global_role="normal_user",
            login_role=target_role,
            new_password=target_password,
        )
        self.assertEqual(create_target.returncode, 0, create_target.stderr)

        create_second_admin = self.run_create_principal(
            actor_user="postgres",
            actor_password="postgres",
            display_name="Other Admin",
            global_role="admin",
            login_role=second_admin_role,
            new_password=second_admin_password,
        )
        self.assertEqual(create_second_admin.returncode, 0, create_second_admin.stderr)

        board_id = self.create_board(slug=self.make_board_slug("delete"), title="Delete Target Board")
        post_id = self.create_post(
            user=target_role,
            password=target_password,
            board_id=board_id,
            title="Delete flow post",
            body="delete flow body",
        )
        review_entry_id = self.create_review_entry(
            user=target_role,
            password=target_password,
            post_id=post_id,
            conclusion="delete flow review",
        )
        with self.connection_for(user=target_role, password=target_password) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "UPDATE app.review_entries SET conclusion = %s WHERE id = %s",
                    ("updated before delete", review_entry_id),
                )
            connection.commit()

        account_id = self.fetch_account_id(target_role)
        disable_result = self.run_manage_account(
            "disable",
            actor_user=admin_role,
            actor_password=admin_password,
            account_id=account_id,
        )
        self.assertEqual(disable_result.returncode, 0, disable_result.stderr)

        other_admin_account_id = self.fetch_account_id(second_admin_role)
        denied_disable_admin = self.run_manage_account(
            "disable",
            actor_user=admin_role,
            actor_password=admin_password,
            account_id=other_admin_account_id,
        )
        self.assertNotEqual(denied_disable_admin.returncode, 0)
        self.assertIn("policy violation", denied_disable_admin.stderr)

        with self.admin_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT account_status::text FROM auth.accounts WHERE id = %s", (account_id,))
                self.assertEqual(cursor.fetchone()[0], "disabled")

        delete_result = self.run_manage_account(
            "delete",
            actor_user=admin_role,
            actor_password=admin_password,
            account_id=account_id,
        )
        self.assertEqual(delete_result.returncode, 0, delete_result.stderr)

        delete_admin_result = self.run_manage_account(
            "delete",
            actor_user="postgres",
            actor_password="postgres",
            account_id=other_admin_account_id,
        )
        self.assertEqual(delete_admin_result.returncode, 0, delete_admin_result.stderr)

        with self.admin_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT id FROM auth.accounts WHERE pg_login_role = 'deleted_account_tombstone'")
                tombstone_account_id = cursor.fetchone()[0]

                cursor.execute("SELECT author_id FROM app.posts WHERE id = %s", (post_id,))
                self.assertEqual(cursor.fetchone()[0], tombstone_account_id)

                cursor.execute("SELECT account_id FROM app.review_entries WHERE id = %s", (review_entry_id,))
                self.assertEqual(cursor.fetchone()[0], tombstone_account_id)

                cursor.execute(
                    "SELECT replaced_by FROM app.review_history WHERE review_entry_id = %s ORDER BY id DESC LIMIT 1",
                    (review_entry_id,),
                )
                self.assertEqual(cursor.fetchone()[0], tombstone_account_id)

                cursor.execute("SELECT count(*) FROM auth.accounts WHERE id = %s", (account_id,))
                self.assertEqual(cursor.fetchone()[0], 0)

                cursor.execute("SELECT to_regrole(%s)", (target_role,))
                self.assertIsNone(cursor.fetchone()[0])
