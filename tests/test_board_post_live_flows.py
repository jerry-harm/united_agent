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


def live_db_env() -> dict[str, str]:
    env = os.environ.copy()
    env.setdefault("AGENT_KB_DB_HOST", "localhost")
    env.setdefault("AGENT_KB_DB_PORT", "5432")
    env.setdefault("AGENT_KB_DB_NAME", "united_agent")
    env.setdefault("AGENT_KB_DB_USER", "postgres")
    env.setdefault("AGENT_KB_DB_PASSWORD", "postgres")
    return env


class LiveBoardPostFlowDocumentationTest(unittest.TestCase):
    def test_readme_documents_live_board_post_flow_test(self) -> None:
        content = (ROOT / "docs/developer-guide.md").read_text(encoding="utf-8")

        self.assertIn("tests/test_board_post_live_flows.py", content)
        self.assertIn("uv run python -m unittest tests.test_board_post_live_flows -v", content)
        self.assertIn("python3 -m unittest tests.test_board_post_live_flows -v", content)
        self.assertIn("已经运行中的本地 PostgreSQL", content)
        self.assertIn("直接 SQL", content)


class LiveBoardPostFlowTest(unittest.TestCase):
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
        self.login_role = f"live_flow_{suffix}"
        self.password = f"pw_{suffix}"
        self.board_slug = f"live-board-{suffix}"
        self.rejected_board_slug = f"live-board-denied-{suffix}"
        self.created_post_ids: list[int] = []

    def tearDown(self) -> None:
        with self.admin_connection(autocommit=True) as connection:
            with connection.cursor() as cursor:
                if self.created_post_ids:
                    cursor.execute(
                        "DELETE FROM app.posts WHERE id = ANY(%s)",
                        (self.created_post_ids,),
                    )
                cursor.execute(
                    "DELETE FROM app.posts WHERE board_id IN (SELECT id FROM app.boards WHERE slug IN (%s, %s))",
                    (self.board_slug, self.rejected_board_slug),
                )
                cursor.execute(
                    "DELETE FROM auth.board_moderators WHERE board_id IN (SELECT id FROM app.boards WHERE slug IN (%s, %s))",
                    (self.board_slug, self.rejected_board_slug),
                )
                cursor.execute(
                    "DELETE FROM app.boards WHERE slug IN (%s, %s)",
                    (self.board_slug, self.rejected_board_slug),
                )
                cursor.execute("DELETE FROM auth.accounts WHERE pg_login_role = %s", (self.login_role,))
                cursor.execute(sql.SQL("DROP ROLE IF EXISTS {}").format(sql.Identifier(self.login_role)))

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

    def principal_connection(self) -> psycopg.Connection:
        return psycopg.connect(
            host=self.env["AGENT_KB_DB_HOST"],
            port=self.env["AGENT_KB_DB_PORT"],
            dbname=self.env["AGENT_KB_DB_NAME"],
            user=self.login_role,
            password=self.password,
        )

    def board_id_for_slug(self, slug: str) -> int:
        with self.admin_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT id FROM app.boards WHERE slug = %s", (slug,))
                row = cursor.fetchone()
        self.assertIsNotNone(row, slug)
        return row[0]

    def create_principal(self, *, login_role: str, password: str, display_name: str, global_role: str = "normal_user") -> None:
        subprocess.run(
            [
                "python3",
                "skills/agent-kb-postgres-admin/scripts/create_principal.py",
                "--principal-type",
                "human",
                "--display-name",
                display_name,
                "--global-role",
                global_role,
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

    def test_live_authorization_paths_match_helper_roles(self) -> None:
        with self.admin_connection() as admin_connection:
            with admin_connection.cursor() as cursor:
                cursor.execute("SELECT auth.current_account_id()")
                admin_account_id = cursor.fetchone()[0]

                cursor.execute(
                    """
                    INSERT INTO app.boards (slug, title, description, board_type, created_by)
                    VALUES (%s, %s, %s, 'discussion', auth.current_account_id())
                    RETURNING id, created_by
                    """,
                    (self.board_slug, "Live Flow Board", "integration test board"),
                )
                board_id, created_by = cursor.fetchone()
                self.assertEqual(created_by, admin_account_id)

            admin_connection.commit()

        self.create_principal(
            login_role=self.login_role,
            password=self.password,
            display_name="Live Flow User",
        )

        with self.admin_connection() as admin_connection:
            with admin_connection.cursor() as cursor:
                cursor.execute(
                    "SELECT id FROM auth.accounts WHERE pg_login_role = %s",
                    (self.login_role,),
                )
                normal_user_account_id = cursor.fetchone()[0]

        with self.principal_connection() as principal_connection:
            with principal_connection.cursor() as cursor:
                cursor.execute(
                    "SELECT auth.current_account_id(), auth.is_admin(), auth.is_super_admin(), auth.can_write()"
                )
                account_id, is_admin, is_super_admin, can_write = cursor.fetchone()
                self.assertEqual(account_id, normal_user_account_id)
                self.assertFalse(is_admin)
                self.assertFalse(is_super_admin)
                self.assertTrue(can_write)

                cursor.execute(
                    """
                    INSERT INTO app.posts (board_id, author_id, content_type, title, body)
                    VALUES (%s, auth.current_account_id(), %s, %s, %s)
                    RETURNING id, author_id, verification
                    """,
                    (board_id, "text/plain", "Live Flow Post", "post body from integration test"),
                )
                post_id, author_id, verification = cursor.fetchone()
                self.created_post_ids.append(post_id)
                self.assertEqual(author_id, normal_user_account_id)
                self.assertEqual(verification, "progressing")
            principal_connection.commit()

        with self.principal_connection() as principal_connection:
            with principal_connection.cursor() as cursor:
                with self.assertRaises(psycopg.Error) as excinfo:
                    cursor.execute(
                        """
                        INSERT INTO app.boards (slug, title, description, board_type, created_by)
                        VALUES (%s, %s, %s, 'discussion', auth.current_account_id())
                        """,
                        (
                            self.rejected_board_slug,
                            "Denied Board",
                            "normal user should not create boards",
                        ),
                    )

                self.assertIn("row-level security", str(excinfo.exception).lower())
                principal_connection.rollback()

        with self.principal_connection() as principal_connection:
            with principal_connection.cursor() as cursor:
                with self.assertRaises(psycopg.Error) as excinfo:
                    cursor.execute(
                        """
                        INSERT INTO auth.board_moderators (board_id, account_id, granted_by)
                        VALUES (%s, auth.current_account_id(), auth.current_account_id())
                        """,
                        (board_id,),
                    )

                self.assertIn("row-level security", str(excinfo.exception).lower())
                principal_connection.rollback()

        with self.principal_connection() as principal_connection:
            with principal_connection.cursor() as cursor:
                with self.assertRaises(psycopg.Error) as excinfo:
                    cursor.execute(
                        """
                        INSERT INTO auth.principal_global_roles (account_id, role_name, granted_by)
                        VALUES (auth.current_account_id(), 'admin', auth.current_account_id())
                        """
                    )

                self.assertIn("row-level security", str(excinfo.exception).lower())
                principal_connection.rollback()

        with self.principal_connection() as principal_connection:
            with principal_connection.cursor() as cursor:
                cursor.execute(
                    "UPDATE app.posts SET verification = 'verified' WHERE id = %s RETURNING verification",
                    (post_id,),
                )

                self.assertEqual(cursor.rowcount, 0)
                self.assertIsNone(cursor.fetchone())

                cursor.execute(
                    "SELECT verification FROM app.posts WHERE id = %s",
                    (post_id,),
                )
                self.assertEqual(cursor.fetchone()[0], "progressing")
                principal_connection.rollback()

        with self.admin_connection() as admin_connection:
            with admin_connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO auth.board_moderators (board_id, account_id, granted_by)
                    VALUES (%s, %s, auth.current_account_id())
                    RETURNING board_id, account_id
                    """,
                    (board_id, normal_user_account_id),
                )
                self.assertEqual(cursor.fetchone(), (board_id, normal_user_account_id))
            admin_connection.commit()

        with self.principal_connection() as principal_connection:
            with principal_connection.cursor() as cursor:
                cursor.execute(
                    "SELECT auth.is_board_moderator(%s)",
                    (board_id,),
                )
                self.assertTrue(cursor.fetchone()[0])

                cursor.execute(
                    "UPDATE app.posts SET verification = 'verified' WHERE id = %s RETURNING verification",
                    (post_id,),
                )
                self.assertEqual(cursor.fetchone()[0], "verified")
            principal_connection.commit()

    def test_announcement_board_is_admin_only_for_posting(self) -> None:
        self.create_principal(
            login_role=self.login_role,
            password=self.password,
            display_name="Announcement Flow User",
        )

        hello_board_id = self.board_id_for_slug("hello")
        governance_board_id = self.board_id_for_slug("governance")
        announcement_board_id = self.board_id_for_slug("announcement")

        with self.principal_connection() as principal_connection:
            with principal_connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO app.posts (board_id, author_id, content_type, title, body)
                    VALUES (%s, auth.current_account_id(), %s, %s, %s)
                    RETURNING id
                    """,
                    (hello_board_id, "text/plain", "Hello Board Post", "ordinary user hello board post"),
                )
                hello_post_id = cursor.fetchone()[0]
                self.created_post_ids.append(hello_post_id)
                self.assertIsInstance(hello_post_id, int)

                cursor.execute(
                    """
                    INSERT INTO app.posts (board_id, author_id, content_type, title, body)
                    VALUES (%s, auth.current_account_id(), %s, %s, %s)
                    RETURNING id
                    """,
                    (governance_board_id, "text/plain", "Governance Board Post", "ordinary user governance request"),
                )
                governance_post_id = cursor.fetchone()[0]
                self.created_post_ids.append(governance_post_id)
                self.assertIsInstance(governance_post_id, int)
            principal_connection.commit()

        with self.principal_connection() as principal_connection:
            with principal_connection.cursor() as cursor:
                with self.assertRaises(psycopg.Error) as excinfo:
                    cursor.execute(
                        """
                        INSERT INTO app.posts (board_id, author_id, content_type, title, body)
                        VALUES (%s, auth.current_account_id(), %s, %s, %s)
                        """,
                        (announcement_board_id, "announcement", "Denied Announcement", "ordinary user should be denied"),
                    )

                self.assertIn("row-level security", str(excinfo.exception).lower())
                principal_connection.rollback()

        with self.admin_connection() as admin_connection:
            with admin_connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO app.posts (board_id, author_id, content_type, title, body)
                    VALUES (%s, auth.current_account_id(), %s, %s, %s)
                    RETURNING id, author_id
                    """,
                    (announcement_board_id, "announcement", "Admin Announcement", "admin announcement post"),
                )
                post_id, author_id = cursor.fetchone()
                self.created_post_ids.append(post_id)
                self.assertIsInstance(post_id, int)

                cursor.execute("SELECT auth.current_account_id()")
                self.assertEqual(author_id, cursor.fetchone()[0])
            admin_connection.commit()


if __name__ == "__main__":
    unittest.main()
