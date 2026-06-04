from __future__ import annotations

import os
from pathlib import Path
import subprocess
import unittest

try:
    import psycopg
    from psycopg import sql
except ModuleNotFoundError:  # pragma: no cover - environment-dependent
    psycopg = None
    sql = None

from tests.live_postgres_helpers import LivePostgresTestCase


ROOT = Path(__file__).resolve().parents[1]
MANAGE_REGISTRATION_TOKEN_SCRIPT = ROOT / "skills/agent-kb-postgres-admin/scripts/manage_registration_token.py"
REGISTER_WITH_TOKEN_SCRIPT = ROOT / "skills/agent-kb-postgres-connect/scripts/register_with_token.py"


class RegistrationTokenLiveFlowTest(LivePostgresTestCase):
    def create_registration_login(self, *, login_role: str, password: str) -> None:
        self.created_roles.add(login_role)
        with self.admin_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    sql.SQL("CREATE ROLE {} LOGIN PASSWORD {}")
                    .format(sql.Identifier(login_role), sql.Literal(password))
                )
            connection.commit()

    def run_manage_registration_token(
        self,
        action: str,
        *,
        actor_user: str,
        actor_password: str,
        max_uses: int | None = None,
        expires_at: str | None = None,
        token_id: int | None = None,
        check: bool = False,
    ) -> subprocess.CompletedProcess[str]:
        args = [action]
        if max_uses is not None:
            args.extend(["--max-uses", str(max_uses)])
        if expires_at is not None:
            args.extend(["--expires-at", expires_at])
        if token_id is not None:
            args.extend(["--token-id", str(token_id)])
        return self.run_python_script(
            MANAGE_REGISTRATION_TOKEN_SCRIPT,
            args,
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
    ) -> subprocess.CompletedProcess[str]:
        env = os.environ.copy()
        env["AGENT_KB_DATABASE_URL"] = f"postgres://{db_user}:{db_password}@localhost:5432/united_agent"
        env["AGENT_KB_NEW_PASSWORD"] = password
        return subprocess.run(
            [
                "python3",
                str(REGISTER_WITH_TOKEN_SCRIPT),
                "--token",
                token,
                "--display-name",
                display_name,
                "--login-role",
                login_role,
                "--new-password-env",
                "AGENT_KB_NEW_PASSWORD",
            ],
            cwd=ROOT,
            env=env,
            check=False,
            capture_output=True,
            text=True,
        )

    def extract_token(self, stdout: str) -> str:
        for line in stdout.splitlines():
            if line.startswith("token="):
                return line.split("=", 1)[1].strip()
        self.fail(f"token= line missing from output: {stdout}")

    def test_admin_can_issue_token_and_register_up_to_quota(self) -> None:
        result = self.run_manage_registration_token(
            "create",
            actor_user="postgres",
            actor_password="postgres",
            max_uses=2,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        token = self.extract_token(result.stdout)

        registration_login = self.make_login_role("registration_guest")
        registration_password = f"pw_{self.suffix}_registration_guest"
        self.create_registration_login(login_role=registration_login, password=registration_password)

        login_role_one = self.make_login_role("reg1")
        login_role_two = self.make_login_role("reg2")
        self.created_roles.update({login_role_one, login_role_two})

        register_one = self.run_register_with_token(
            db_user=registration_login,
            db_password=registration_password,
            token=token,
            login_role=login_role_one,
            password=f"pw_{self.suffix}_1",
            display_name="Registration User One",
        )
        self.assertEqual(register_one.returncode, 0, register_one.stderr)
        self.assertIn("registration ok", register_one.stdout)

        register_two = self.run_register_with_token(
            db_user=registration_login,
            db_password=registration_password,
            token=token,
            login_role=login_role_two,
            password=f"pw_{self.suffix}_2",
            display_name="Registration User Two",
        )
        self.assertEqual(register_two.returncode, 0, register_two.stderr)

        login_role_three = self.make_login_role("reg3")
        self.created_roles.add(login_role_three)
        register_three = self.run_register_with_token(
            db_user=registration_login,
            db_password=registration_password,
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
            "create",
            actor_user=normal_user,
            actor_password=f"pw_{self.suffix}",
            max_uses=1,
            check=False,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("not admin", result.stderr)


if __name__ == "__main__":
    unittest.main()
