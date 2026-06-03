from __future__ import annotations

import os
import re
from pathlib import Path

import psycopg
from psycopg import sql


ROOT = Path(__file__).resolve().parents[1]


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


def sql_file(relative_path: str) -> Path:
    return ROOT / relative_path


PLACEHOLDER_RE = re.compile(r"\{\{\s*([a-z_][a-z0-9_]*)\s*\}\}")


def render_sql(connection: psycopg.Connection, template: str, variables: dict[str, str]) -> str:
    def replace(match: re.Match[str]) -> str:
        name = match.group(1)
        if name not in variables:
            raise SystemExit(f"missing SQL variable: {name}")
        return sql.Literal(variables[name]).as_string(connection)

    return PLACEHOLDER_RE.sub(replace, template)


def run_sql_file(sql_path: Path, variables: dict[str, str]) -> int:
    env = db_env()
    with psycopg.connect(
        host=env["host"],
        port=env["port"],
        dbname=env["name"],
        user=env["user"],
        password=env["password"],
    ) as connection:
        connection.autocommit = False
        rendered_sql = render_sql(connection, sql_path.read_text(encoding="utf-8"), variables)
        with connection.cursor() as cursor:
            cursor.execute(rendered_sql)
            if cursor.description:
                rows = cursor.fetchall()
                print_table(cursor, rows)
        connection.commit()
    return 0


def open_connection() -> psycopg.Connection:
    env = db_env()
    return psycopg.connect(
        host=env["host"],
        port=env["port"],
        dbname=env["name"],
        user=env["user"],
        password=env["password"],
    )


def require_admin(connection: psycopg.Connection, *, need_super_admin: bool = False) -> None:
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT auth.is_admin(), auth.is_super_admin(), auth.can_write(), auth.current_account_id()"
        )
        is_admin, is_super_admin, can_write, account_id = cursor.fetchone()
    if account_id is None:
        raise SystemExit("login resolved to no auth.accounts row")
    if need_super_admin and not is_super_admin:
        raise SystemExit("not super_admin")
    if not is_admin:
        raise SystemExit("not admin")
    if not can_write:
        raise SystemExit("account is not active; admin operations require auth.can_write")


def print_table(cursor: psycopg.Cursor, rows: list[tuple]) -> None:
    if cursor.description is None:
        return
    columns = [column.name for column in cursor.description]
    if not rows:
        print("no rows")
        return
    str_rows: list[list[str]] = [
        ["" if value is None else str(value) for value in row] for row in rows
    ]
    widths = [len(column) for column in columns]
    for row in str_rows:
        for index, cell in enumerate(row):
            widths[index] = max(widths[index], len(cell))
    header = " | ".join(column.ljust(widths[index]) for index, column in enumerate(columns))
    separator = "-+-".join("-" * width for width in widths)
    print(header)
    print(separator)
    for row in str_rows:
        print(" | ".join(cell.ljust(widths[index]) for index, cell in enumerate(row)))
