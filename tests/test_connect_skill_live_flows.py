from __future__ import annotations

import os
from pathlib import Path
import subprocess
import unittest
import uuid

try:
    import psycopg
    from psycopg import sql
except ModuleNotFoundError:  # pragma: no cover - environment-dependent
    psycopg = None
    sql = None


ROOT = Path(__file__).resolve().parents[1]
VERIFY_CONNECTION_SCRIPT = ROOT / "skills/agent-kb-postgres-connect/scripts/verify_connection.py"


def live_db_env() -> dict[str, str]:
    env = os.environ.copy()
    env.setdefault("AGENT_KB_DB_HOST", "localhost")
    env.setdefault("AGENT_KB_DB_PORT", "5432")
    env.setdefault("AGENT_KB_DB_NAME", "united_agent")
    env.setdefault("AGENT_KB_DB_USER", "postgres")
    env.setdefault("AGENT_KB_DB_PASSWORD", "postgres")
    return env


class LiveConnectSkillDocumentationTest(unittest.TestCase):
    def test_readme_documents_live_connect_skill_test(self) -> None:
        content = (ROOT / "README.md").read_text(encoding="utf-8")

        self.assertIn("tests/test_connect_skill_live_flows.py", content)
        self.assertIn("python3 -m unittest tests.test_connect_skill_live_flows -v", content)
        self.assertIn("verify_connection.py", content)


class LiveConnectSkillTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        if psycopg is None:
            raise unittest.SkipTest('psycopg is required for live PostgreSQL integration tests; install with pip install "psycopg[binary]"')
        cls.env = live_db_env()
        try:
            with psycopg.connect(
                host=cls.env["AGENT_KB_DB_HOST"],
                port=cls.env["AGENT_KB_DB_PORT"],
                dbname=cls.env["AGENT_KB_DB_NAME"],
                user=cls.env["AGENT_KB_DB_USER"],
                password=cls.env["AGENT_KB_DB_PASSWORD"],
            ):
                pass
        except psycopg.Error as exc:
            raise unittest.SkipTest(f"live PostgreSQL is required for this test: {exc}") from exc

    def setUp(self) -> None:
        suffix = uuid.uuid4().hex[:8]
        self.login_role = f"connect_flow_{suffix}"
        self.password = f"pw_{suffix}"
        self.unmapped_role = f"connect_unmapped_{suffix}"

    def tearDown(self) -> None:
        with self.admin_connection(autocommit=True) as connection:
            with connection.cursor() as cursor:
                cursor.execute("DELETE FROM auth.accounts WHERE pg_login_role IN (%s, %s)", (self.login_role, self.unmapped_role))
                cursor.execute(sql.SQL("DROP ROLE IF EXISTS {}").format(sql.Identifier(self.login_role)))
                cursor.execute(sql.SQL("DROP ROLE IF EXISTS {}").format(sql.Identifier(self.unmapped_role)))

    def admin_connection(self, autocommit: bool = False) -> psycopg.Connection:
        connection = psycopg.connect(
            host=self.env["AGENT_KB_DB_HOST"],
            port=self.env["AGENT_KB_DB_PORT"],
            dbname=self.env["AGENT_KB_DB_NAME"],
            user=self.env["AGENT_KB_DB_USER"],
            password=self.env["AGENT_KB_DB_PASSWORD"],
        )
        connection.autocommit = autocommit
        return connection

    def create_principal(self, *, login_role: str, password: str, display_name: str) -> None:
        subprocess.run(
            [
                "python3",
                "skills/agent-kb-postgres-admin/scripts/create_principal.py",
                "--principal-type",
                "human",
                "--display-name",
                display_name,
                "--global-role",
                "normal_user",
                "--login-role",
                login_role,
                "--new-password",
                password,
            ],
            cwd=ROOT,
            env=self.env,
            check=True,
            capture_output=True,
            text=True,
        )

    def run_connect_script(self, *, user: str, password: str, extra_env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
        env = self.env | {
            "AGENT_KB_DB_USER": user,
            "AGENT_KB_DB_PASSWORD": password,
        }
        if extra_env:
            env.update(extra_env)
        return subprocess.run(
            ["python3", str(VERIFY_CONNECTION_SCRIPT)],
            cwd=ROOT,
            env=env,
            check=False,
            capture_output=True,
            text=True,
        )

    def test_bundled_connect_script_reports_successful_identity(self) -> None:
        self.create_principal(
            login_role=self.login_role,
            password=self.password,
            display_name="Connect Flow User",
        )

        result = self.run_connect_script(
            user=self.login_role,
            password=self.password,
            extra_env={
                "AGENT_KB_EXPECTED_LOGIN_ROLE": self.login_role,
                "AGENT_KB_EXPECTED_DISPLAY_NAME": "Connect Flow User",
            },
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("connection ok", result.stdout)
        self.assertIn(f"pg_login_role={self.login_role}", result.stdout)
        self.assertIn("account_status=active", result.stdout)
        self.assertIn("display_name=Connect Flow User", result.stdout)

    def test_bundled_connect_script_fails_for_unmapped_login(self) -> None:
        with self.admin_connection(autocommit=True) as connection:
            with connection.cursor() as cursor:
                cursor.execute(sql.SQL("CREATE ROLE {} LOGIN PASSWORD %s").format(sql.Identifier(self.unmapped_role)), (self.password,))
                cursor.execute(sql.SQL("GRANT united_agent_user TO {}").format(sql.Identifier(self.unmapped_role)))

        result = self.run_connect_script(user=self.unmapped_role, password=self.password)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("login resolved to no auth.accounts row", result.stderr)

    def test_bundled_connect_script_fails_for_inactive_account(self) -> None:
        self.create_principal(
            login_role=self.login_role,
            password=self.password,
            display_name="Disabled Connect User",
        )
        with self.admin_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "UPDATE auth.accounts SET account_status = 'disabled' WHERE pg_login_role = %s",
                    (self.login_role,),
                )
            connection.commit()

        result = self.run_connect_script(user=self.login_role, password=self.password)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("is not active: disabled", result.stderr)


if __name__ == "__main__":
    unittest.main()
