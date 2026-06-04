from __future__ import annotations

import os
from pathlib import Path
from urllib.parse import urlsplit

import psycopg
from psycopg import sql


IDENTITY_QUERY = """
SELECT
    current_user,
    session_user,
    auth.current_account_id(),
    auth.current_account_status(),
    p.display_name,
    a.pg_login_role
FROM auth.accounts AS a
LEFT JOIN app.profiles AS p ON p.account_id = a.id
WHERE a.id = auth.current_account_id();
"""


def require_env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise SystemExit(f"missing required environment variable: {name}")
    return value


def load_secret_from_env_name(env_name: str) -> str:
    name = env_name.strip()
    if not name:
        raise SystemExit("explicit environment variable name is required")
    return require_env(name)


def db_env(url_from_flag: str | None = None) -> dict[str, str]:
    if url_from_flag:
        u = urlsplit(url_from_flag)
        return {
            "host": u.hostname or "",
            "user": u.username or "",
            "password": u.password or "",
            "port": str(u.port or 5432),
            "name": u.path.lstrip("/") or "",
        }
    if os.environ.get("AGENT_KB_DATABASE_URL"):
        u = urlsplit(os.environ["AGENT_KB_DATABASE_URL"])
        return {
            "host": u.hostname or "",
            "user": u.username or "",
            "password": u.password or "",
            "port": str(u.port or 5432),
            "name": u.path.lstrip("/") or "",
        }
    raise SystemExit("database URL is required (set AGENT_KB_DATABASE_URL or use --url)")


def connect(url_from_flag: str | None = None) -> psycopg.Connection:
    env = db_env(url_from_flag)
    return psycopg.connect(
        host=env["host"],
        port=env["port"],
        dbname=env["name"],
        user=env["user"],
        password=env["password"],
    )


def load_identity_row(connection: psycopg.Connection) -> tuple[str, str, int, str, str, str] | None:
    with connection.cursor() as cursor:
        cursor.execute(IDENTITY_QUERY)
        return cursor.fetchone()


def format_identity_row(row: tuple[str, str, int, str, str, str]) -> list[str]:
    current_user, session_user, account_id, account_status, display_name, pg_login_role = row
    return [
        "connection ok",
        f"current_user={current_user}",
        f"session_user={session_user}",
        f"account_id={account_id}",
        f"account_status={account_status}",
        f"display_name={display_name}",
        f"pg_login_role={pg_login_role}",
    ]


def render_sql(connection: psycopg.Connection, sql_path: str, variables: dict[str, str] | None = None) -> str:
    raw = (Path(__file__).parent / sql_path).read_text(encoding="utf-8")
    if not variables:
        return raw
    rendered = raw
    for key, val in (variables or {}).items():
        rendered = rendered.replace(f"{{{key}}}", val)
    return rendered
