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
VALIDATE_POST_FLOW_SCRIPT = ROOT / "skills/agent-kb-postgres-connect/scripts/validate_post_flow.py"
VALIDATE_REVIEW_FLOW_SCRIPT = ROOT / "skills/agent-kb-postgres-connect/scripts/validate_review_flow.py"


def live_db_env() -> dict[str, str]:
    env = os.environ.copy()
    if env.get("AGENT_KB_DATABASE_URL"):
        from urllib.parse import urlsplit

        u = urlsplit(env["AGENT_KB_DATABASE_URL"])
        env["AGENT_KB_DB_HOST"] = u.hostname or "localhost"
        env["AGENT_KB_DB_PORT"] = str(u.port or 5432)
        env["AGENT_KB_DB_NAME"] = u.path.lstrip("/") or "united_agent"
        env["AGENT_KB_DB_USER"] = u.username or "postgres"
        env["AGENT_KB_DB_PASSWORD"] = u.password or "postgres"
    else:
        env.setdefault("AGENT_KB_DB_HOST", "localhost")
        env.setdefault("AGENT_KB_DB_PORT", "5432")
        env.setdefault("AGENT_KB_DB_NAME", "united_agent")
        env.setdefault("AGENT_KB_DB_USER", "postgres")
        env.setdefault("AGENT_KB_DB_PASSWORD", "postgres")
    return env


class LiveConnectSkillDocumentationTest(unittest.TestCase):
    def test_readme_documents_live_connect_skill_test(self) -> None:
        content = (ROOT / "docs/developer-guide.md").read_text(encoding="utf-8")

        self.assertIn("tests/test_connect_skill_live_flows.py", content)
        self.assertIn("uv run python -m unittest tests.test_connect_skill_live_flows -v", content)
        self.assertIn("python3 -m unittest tests.test_connect_skill_live_flows -v", content)
        self.assertIn("verify_connection.py", content)
        self.assertIn("validate_post_flow.py", content)
        self.assertIn("validate_review_flow.py", content)


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

    def create_board(self, *, slug: str, title: str) -> int:
        with self.admin_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO app.boards (slug, title, description, board_type, created_by)
                    VALUES (%s, %s, %s, 'discussion', auth.current_account_id())
                    RETURNING id
                    """,
                    (slug, title, "connect skill validation board"),
                )
                board_id = cursor.fetchone()[0]
            connection.commit()
        return board_id

    def create_post(self, *, user: str, password: str, board_id: int, title: str, body: str) -> int:
        connection_factory = self.admin_connection if user == "postgres" and password == "postgres" else lambda: psycopg.connect(
            host=self.env["AGENT_KB_DB_HOST"],
            port=self.env["AGENT_KB_DB_PORT"],
            dbname=self.env["AGENT_KB_DB_NAME"],
            user=user,
            password=password,
        )
        with connection_factory() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO app.posts (board_id, author_id, content_type, title, body)
                    VALUES (%s, auth.current_account_id(), %s, %s, %s)
                    RETURNING id
                    """,
                    (board_id, "text/plain", title, body),
                )
                post_id = cursor.fetchone()[0]
            connection.commit()
        return post_id

    def run_connect_script(self, *, user: str, password: str, extra_env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
        db_url = f"postgres://{user}:{password}@{self.env['AGENT_KB_DB_HOST']}:{self.env['AGENT_KB_DB_PORT']}/{self.env['AGENT_KB_DB_NAME']}"
        env = self.env | {"AGENT_KB_DATABASE_URL": db_url}
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

    def test_validate_post_flow_script_reports_success_for_normal_user(self) -> None:
        board_slug = f"connect-post-{uuid.uuid4().hex[:8]}"
        login_role = f"connect_post_{uuid.uuid4().hex[:8]}"
        password = f"pw_{uuid.uuid4().hex[:8]}"
        self.create_principal(login_role=login_role, password=password, display_name="Connect Post User")
        board_id = self.create_board(slug=board_slug, title="Connect Post Board")

        result = subprocess.run(
            ["python3", str(VALIDATE_POST_FLOW_SCRIPT), "--board-id", str(board_id)],
            cwd=ROOT,
            env=self.env | {"AGENT_KB_DATABASE_URL": f"postgres://{login_role}:{password}@{self.env['AGENT_KB_DB_HOST']}:{self.env['AGENT_KB_DB_PORT']}/{self.env['AGENT_KB_DB_NAME']}"},
            check=False,
            capture_output=True,
            text=True,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("post flow ok", result.stdout)
        self.assertIn("post created", result.stdout)

    def test_validate_review_flow_script_reports_success_for_normal_user(self) -> None:
        board_slug = f"connect-review-{uuid.uuid4().hex[:8]}"
        login_role = f"connect_review_{uuid.uuid4().hex[:8]}"
        password = f"pw_{uuid.uuid4().hex[:8]}"
        self.create_principal(login_role=login_role, password=password, display_name="Connect Review User")
        board_id = self.create_board(slug=board_slug, title="Connect Review Board")
        post_id = self.create_post(user=login_role, password=password, board_id=board_id, title="Review target", body="body")

        result = subprocess.run(
            ["python3", str(VALIDATE_REVIEW_FLOW_SCRIPT), "--post-id", str(post_id)],
            cwd=ROOT,
            env=self.env | {"AGENT_KB_DATABASE_URL": f"postgres://{login_role}:{password}@{self.env['AGENT_KB_DB_HOST']}:{self.env['AGENT_KB_DB_PORT']}/{self.env['AGENT_KB_DB_NAME']}"},
            check=False,
            capture_output=True,
            text=True,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("review flow ok", result.stdout)
        self.assertIn("review entry created", result.stdout)


if __name__ == "__main__":
    unittest.main()
