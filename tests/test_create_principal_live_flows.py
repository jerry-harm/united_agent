from __future__ import annotations

import unittest

from tests.live_postgres_helpers import ROOT, LivePostgresTestCase


class LiveCreatePrincipalDocumentationTest(unittest.TestCase):
    def test_readme_documents_live_create_principal_flow_test(self) -> None:
        content = (ROOT / "README.md").read_text(encoding="utf-8")

        self.assertIn("tests/test_create_principal_live_flows.py", content)
        self.assertIn("python3 -m unittest tests.test_create_principal_live_flows -v", content)
        self.assertIn("create_principal.py", content)


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
