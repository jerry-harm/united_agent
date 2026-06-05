from __future__ import annotations

from pathlib import Path
import unittest

try:
    import psycopg
    from psycopg import sql
except ModuleNotFoundError:  # pragma: no cover - environment-dependent
    psycopg = None
    sql = None

from tests.live_postgres_helpers import LivePostgresTestCase


ROOT = Path(__file__).resolve().parents[1]


class RegistrationTokenLiveFlowTest(LivePostgresTestCase):
    def run_manage_registration_token(
        self,
        *,
        actor_user: str,
        actor_password: str,
        token: str,
        max_uses: int | None = None,
        expires_at: str | None = None,
        check: bool = False,
    ):
        helper_args = [token, str(max_uses if max_uses is not None else 1)]
        helper_args.append(expires_at if expires_at is not None else "json:null")
        return self.run_helper_script(
            "auth.issue_registration_token",
            helper_args,
            user=actor_user,
            password=actor_password,
            check=check,
        )

    def run_register_with_token(
        self,
        *,
        db_user: str,
        db_password: str,
        token: str,
        login_role: str,
        password: str,
        display_name: str,
    ):
        self.created_roles.add(login_role)
        return self.run_helper_script(
            "auth.register_with_token",
            [token, "human", display_name, login_role, "env:AGENT_KB_NEW_PASSWORD"],
            user=db_user,
            password=db_password,
            extra_env={"AGENT_KB_NEW_PASSWORD": password},
        )

    def test_admin_can_issue_token_and_register_up_to_quota(self) -> None:
        result = self.run_manage_registration_token(
            actor_user="postgres",
            actor_password="postgres",
            token=f"token_{self.suffix}",
            max_uses=2,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        token = f"token_{self.suffix}"

        login_role_one = self.make_login_role("reg1")
        login_role_two = self.make_login_role("reg2")
        self.created_roles.update({login_role_one, login_role_two})

        register_one = self.run_register_with_token(
            db_user="guest",
            db_password="guest",
            token=token,
            login_role=login_role_one,
            password=f"pw_{self.suffix}_1",
            display_name="Registration User One",
        )
        self.assertEqual(register_one.returncode, 0, register_one.stderr)
        self.assertIn("display_name", register_one.stdout)
        self.assertIn("Registration User One", register_one.stdout)

        register_two = self.run_register_with_token(
            db_user="guest",
            db_password="guest",
            token=token,
            login_role=login_role_two,
            password=f"pw_{self.suffix}_2",
            display_name="Registration User Two",
        )
        self.assertEqual(register_two.returncode, 0, register_two.stderr)

        login_role_three = self.make_login_role("reg3")
        self.created_roles.add(login_role_three)
        register_three = self.run_register_with_token(
            db_user="guest",
            db_password="guest",
            token=token,
            login_role=login_role_three,
            password=f"pw_{self.suffix}_3",
            display_name="Registration User Three",
        )
        self.assertNotEqual(register_three.returncode, 0)
        self.assertIn("registration token has no remaining uses", register_three.stderr)

    def test_non_admin_cannot_issue_registration_token(self) -> None:
        normal_user = self.make_login_role("issuer")
        self.run_create_principal(
            actor_user="postgres",
            actor_password="postgres",
            display_name="Token Issuer User",
            login_role=normal_user,
            new_password=f"pw_{self.suffix}",
            check=True,
        )

        result = self.run_manage_registration_token(
            actor_user=normal_user,
            actor_password=f"pw_{self.suffix}",
            token=f"denied_{self.suffix}",
            max_uses=1,
            check=False,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("only admin or super_admin may create registration tokens", result.stderr)


if __name__ == "__main__":
    unittest.main()
