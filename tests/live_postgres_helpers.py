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
CREATE_PRINCIPAL_SCRIPT = ROOT / "skills/agent-kb-postgres-admin/scripts/create_principal.py"
MANAGE_ACCOUNT_SCRIPT = ROOT / "skills/agent-kb-postgres-admin/scripts/manage_account.py"
MANAGE_GLOBAL_ROLE_SCRIPT = ROOT / "skills/agent-kb-postgres-admin/scripts/manage_global_role.py"


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
    env.setdefault(
        "AGENT_KB_DATABASE_URL",
        f"postgres://{env['AGENT_KB_DB_USER']}:{env['AGENT_KB_DB_PASSWORD']}@{env['AGENT_KB_DB_HOST']}:{env['AGENT_KB_DB_PORT']}/{env['AGENT_KB_DB_NAME']}",
    )
    return env


class LivePostgresTestCase(unittest.TestCase):
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
        self.suffix = uuid.uuid4().hex[:8]
        self.created_roles: set[str] = set()
        self.created_category_slugs: set[str] = set()
        self.created_tag_names: set[str] = set()
        self.created_uploaded_file_ids: set[int] = set()

    def tearDown(self) -> None:
        with self.admin_connection(autocommit=True) as connection:
            with connection.cursor() as cursor:
                account_ids = self.account_ids_for_cleanup(cursor)
                category_ids = self.category_ids_for_cleanup(cursor)
                tag_ids = self.tag_ids_for_cleanup(cursor)
                uploaded_file_ids = self.uploaded_file_ids_for_cleanup(cursor, account_ids)
                post_ids = self.post_ids_for_cleanup(cursor, account_ids, category_ids)
                review_entry_ids = self.review_entry_ids_for_cleanup(cursor, account_ids, post_ids)

                if post_ids or tag_ids:
                    cursor.execute(
                        "DELETE FROM app.post_tags WHERE post_id = ANY(%s) OR tag_id = ANY(%s)",
                        (post_ids, tag_ids),
                    )
                if review_entry_ids:
                    cursor.execute("DELETE FROM app.review_history WHERE review_entry_id = ANY(%s)", (review_entry_ids,))
                if uploaded_file_ids:
                    cursor.execute("DELETE FROM app.uploaded_files WHERE id = ANY(%s)", (uploaded_file_ids,))
                if review_entry_ids or post_ids or account_ids:
                    cursor.execute(
                        "DELETE FROM app.review_entries WHERE id = ANY(%s) OR post_id = ANY(%s) OR account_id = ANY(%s)",
                        (review_entry_ids, post_ids, account_ids),
                    )
                if post_ids or category_ids or account_ids:
                    cursor.execute(
                        "DELETE FROM app.posts WHERE id = ANY(%s) OR category_id = ANY(%s) OR author_id = ANY(%s)",
                        (post_ids, category_ids, account_ids),
                    )
                if tag_ids or account_ids:
                    cursor.execute(
                        "DELETE FROM app.tags WHERE id = ANY(%s) OR created_by = ANY(%s)",
                        (tag_ids, account_ids),
                    )
                if category_ids:
                    cursor.execute("DELETE FROM app.categories WHERE id = ANY(%s)", (category_ids,))
                if account_ids:
                    cursor.execute("DELETE FROM auth.principal_global_roles WHERE account_id = ANY(%s)", (account_ids,))
                    cursor.execute("DELETE FROM auth.accounts WHERE id = ANY(%s)", (account_ids,))
                for role_name in sorted(self.created_roles):
                    cursor.execute(sql.SQL("DROP ROLE IF EXISTS {}").format(sql.Identifier(role_name)))

    def account_ids_for_cleanup(self, cursor: psycopg.Cursor) -> list[int]:
        if not self.created_roles:
            return []
        cursor.execute(
            "SELECT id FROM auth.accounts WHERE pg_login_role = ANY(%s)",
            (sorted(self.created_roles),),
        )
        return [row[0] for row in cursor.fetchall()]

    def category_ids_for_cleanup(self, cursor: psycopg.Cursor) -> list[int]:
        if not self.created_category_slugs:
            return []
        cursor.execute(
            "SELECT id FROM app.categories WHERE slug = ANY(%s)",
            (sorted(self.created_category_slugs),),
        )
        return [row[0] for row in cursor.fetchall()]

    def tag_ids_for_cleanup(self, cursor: psycopg.Cursor) -> list[int]:
        if not self.created_tag_names:
            return []
        cursor.execute(
            "SELECT id FROM app.tags WHERE name = ANY(%s)",
            (sorted(self.created_tag_names),),
        )
        return [row[0] for row in cursor.fetchall()]

    def post_ids_for_cleanup(self, cursor: psycopg.Cursor, account_ids: list[int], category_ids: list[int]) -> list[int]:
        cursor.execute(
            "SELECT id FROM app.posts WHERE category_id = ANY(%s) OR author_id = ANY(%s)",
            (category_ids, account_ids),
        )
        return [row[0] for row in cursor.fetchall()]

    def uploaded_file_ids_for_cleanup(self, cursor: psycopg.Cursor, account_ids: list[int]) -> list[int]:
        ids = sorted(self.created_uploaded_file_ids)
        if account_ids:
            cursor.execute(
                "SELECT id FROM app.uploaded_files WHERE id = ANY(%s) OR uploader_account_id = ANY(%s)",
                (ids, account_ids),
            )
            return [row[0] for row in cursor.fetchall()]
        return ids

    def review_entry_ids_for_cleanup(self, cursor: psycopg.Cursor, account_ids: list[int], post_ids: list[int]) -> list[int]:
        cursor.execute(
            "SELECT id FROM app.review_entries WHERE post_id = ANY(%s) OR account_id = ANY(%s)",
            (post_ids, account_ids),
        )
        return [row[0] for row in cursor.fetchall()]

    def admin_connection(self, autocommit: bool = False) -> psycopg.Connection:
        return self.connection_for(
            user=self.env["AGENT_KB_DB_USER"],
            password=self.env["AGENT_KB_DB_PASSWORD"],
            autocommit=autocommit,
        )

    def connection_for(self, *, user: str, password: str, autocommit: bool = False) -> psycopg.Connection:
        connection = psycopg.connect(
            host=self.env["AGENT_KB_DB_HOST"],
            port=int(self.env["AGENT_KB_DB_PORT"]),
            dbname=self.env["AGENT_KB_DB_NAME"],
            user=user,
            password=password,
        )
        connection.autocommit = autocommit
        return connection

    def make_login_role(self, label: str) -> str:
        role_name = f"lp_{label}_{self.suffix}".replace("-", "_")
        return role_name[:63]

    def make_category_slug(self, label: str) -> str:
        slug = f"live-{label}-{self.suffix}"
        self.created_category_slugs.add(slug)
        return slug

    def make_tag_name(self, label: str) -> str:
        name = f"tag-{label}-{self.suffix}"
        self.created_tag_names.add(name)
        return name

    def run_python_script(
        self,
        script_path: Path,
        args: list[str],
        *,
        user: str,
        password: str,
        check: bool = False,
    ) -> subprocess.CompletedProcess[str]:
        from urllib.parse import urlencode

        db_url = f"postgres://{user}:{password}@{self.env['AGENT_KB_DB_HOST']}:{self.env['AGENT_KB_DB_PORT']}/{self.env['AGENT_KB_DB_NAME']}"
        env = self.env | {"AGENT_KB_DATABASE_URL": db_url}
        return subprocess.run(
            ["python3", str(script_path), *args],
            cwd=ROOT,
            env=env,
            check=check,
            capture_output=True,
            text=True,
        )

    def run_create_principal(
        self,
        *,
        actor_user: str,
        actor_password: str,
        principal_type: str = "human",
        display_name: str,
        global_role: str = "normal_user",
        login_role: str,
        new_password: str,
        check: bool = False,
    ) -> subprocess.CompletedProcess[str]:
        self.created_roles.add(login_role)
        return self.run_python_script(
            CREATE_PRINCIPAL_SCRIPT,
            [
                "--principal-type",
                principal_type,
                "--display-name",
                display_name,
                "--global-role",
                global_role,
                "--login-role",
                login_role,
                "--new-password",
                new_password,
            ],
            user=actor_user,
            password=actor_password,
            check=check,
        )

    def run_manage_account(
        self,
        action: str,
        *,
        actor_user: str,
        actor_password: str,
        account_id: int,
        check: bool = False,
    ) -> subprocess.CompletedProcess[str]:
        return self.run_python_script(
            MANAGE_ACCOUNT_SCRIPT,
            [action, "--account-id", str(account_id)],
            user=actor_user,
            password=actor_password,
            check=check,
        )

    def run_manage_global_role(
        self,
        action: str,
        *,
        actor_user: str,
        actor_password: str,
        account_id: int | None = None,
        role_name: str | None = None,
        check: bool = False,
    ) -> subprocess.CompletedProcess[str]:
        args = [action]
        if account_id is not None:
            args.extend(["--account-id", str(account_id)])
        if role_name is not None:
            args.extend(["--role-name", role_name])
        return self.run_python_script(
            MANAGE_GLOBAL_ROLE_SCRIPT,
            args,
            user=actor_user,
            password=actor_password,
            check=check,
        )

    def create_category(self, *, slug: str | None = None, title: str = "Live Category", description: str = "integration category") -> int:
        category_slug = slug or self.make_category_slug("category")
        with self.admin_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO app.categories (slug, title, description, category_type, created_by)
                    VALUES (%s, %s, %s, 'discussion', auth.current_account_id())
                    RETURNING id
                    """,
                    (category_slug, title, description),
                )
                category_id = cursor.fetchone()[0]
            connection.commit()
        return category_id

    def create_post(self, *, user: str, password: str, category_id: int, title: str, body: str) -> int:
        with self.connection_for(user=user, password=password) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO app.posts (category_id, author_id, content_type, title, body)
                    VALUES (%s, auth.current_account_id(), %s, %s, %s)
                    RETURNING id
                    """,
                    (category_id, "text/plain", title, body),
                )
                post_id = cursor.fetchone()[0]
            connection.commit()
        return post_id

    def create_review_entry(
        self,
        *,
        user: str,
        password: str,
        post_id: int,
        lgtm: bool = False,
        conclusion: str = "initial review",
    ) -> int:
        with self.connection_for(user=user, password=password) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO app.review_entries (post_id, account_id, lgtm, conclusion)
                    VALUES (%s, auth.current_account_id(), %s, %s)
                    RETURNING id
                    """,
                    (post_id, lgtm, conclusion),
                )
                review_entry_id = cursor.fetchone()[0]
            connection.commit()
        return review_entry_id

    def create_tag(self, *, user: str, password: str, name: str | None = None) -> int:
        tag_name = name or self.make_tag_name("tag")
        with self.connection_for(user=user, password=password) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO app.tags (name, created_by)
                    VALUES (%s, auth.current_account_id())
                    RETURNING id
                    """,
                    (tag_name,),
                )
                tag_id = cursor.fetchone()[0]
            connection.commit()
        return tag_id

    def create_uploaded_file(self, *, user: str, password: str, filename: str, mime_type: str, content: str) -> int:
        with self.connection_for(user=user, password=password) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO app.uploaded_files (filename, uploader_account_id, mime_type, content)
                    VALUES (%s, auth.current_account_id(), %s, %s)
                    RETURNING id
                    """,
                    (filename, mime_type, content),
                )
                uploaded_file_id = cursor.fetchone()[0]
            connection.commit()
        self.created_uploaded_file_ids.add(uploaded_file_id)
        return uploaded_file_id

    def fetch_account_id(self, login_role: str) -> int:
        with self.admin_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT id FROM auth.accounts WHERE pg_login_role = %s", (login_role,))
                row = cursor.fetchone()
        self.assertIsNotNone(row, login_role)
        return row[0]

    def set_account_status(self, login_role: str, status: str) -> None:
        with self.admin_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "UPDATE auth.accounts SET account_status = %s WHERE pg_login_role = %s",
                    (status, login_role),
                )
            connection.commit()

    def fetch_role_flags(self, *, user: str, password: str) -> tuple[bool, bool, bool, str]:
        with self.connection_for(user=user, password=password) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT auth.is_admin(), auth.is_super_admin(), auth.can_write(), auth.current_account_status()::text"
                )
                is_admin, is_super_admin, can_write, status = cursor.fetchone()
                return is_admin, is_super_admin, can_write, status

    def assert_write_denied(self, operation) -> Exception | None:
        try:
            outcome = operation()
        except psycopg.Error as exc:
            self.assertRegex(str(exc).lower(), r"row-level security|policy violation|permission denied")
            return exc
        else:
            self.assertEqual(outcome, 0)
            return None
