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
        "name": os.environ.get("AGENT_KB_DB_NAME", "agent_knowledge_base"),
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
                for row in cursor.fetchall():
                    print("\t".join("" if value is None else str(value) for value in row))
        connection.commit()
    return 0
