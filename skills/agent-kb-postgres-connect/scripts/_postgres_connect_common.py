from __future__ import annotations

import os

import psycopg


IDENTITY_QUERY = """
SELECT
    current_user,
    session_user,
    auth.current_account_id(),
    auth.current_account_status(),
    a.display_name,
    a.pg_login_role
FROM auth.accounts AS a
WHERE a.id = auth.current_account_id();
"""


def require_env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise SystemExit(f"missing required environment variable: {name}")
    return value


def db_env() -> dict[str, str]:
    return {
        "host": require_env("AGENT_KB_DB_HOST"),
        "user": require_env("AGENT_KB_DB_USER"),
        "password": require_env("AGENT_KB_DB_PASSWORD"),
        "port": os.environ.get("AGENT_KB_DB_PORT", "5432"),
        "name": os.environ.get("AGENT_KB_DB_NAME", "united_agent"),
    }


def connect() -> psycopg.Connection:
    env = db_env()
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
