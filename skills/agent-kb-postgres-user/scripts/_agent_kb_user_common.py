from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import NoReturn
from urllib.parse import urlsplit

import psycopg
from psycopg import sql


ROOT = Path(__file__).resolve().parents[1]
HELPER_NAME_RE = re.compile(r"^(?P<schema>[a-z_][a-z0-9_]*)\.(?P<name>[a-z_][a-z0-9_]*)$")
PLACEHOLDER_RE = re.compile(r"\{\{\s*([a-z_][a-z0-9_]*)\s*\}\}")


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
        parsed = urlsplit(url_from_flag)
    elif os.environ.get("AGENT_KB_DATABASE_URL"):
        parsed = urlsplit(os.environ["AGENT_KB_DATABASE_URL"])
    else:
        raise SystemExit("database URL is required (set AGENT_KB_DATABASE_URL or use --url)")

    return {
        "host": parsed.hostname or "",
        "user": parsed.username or "",
        "password": parsed.password or "",
        "port": str(parsed.port or 5432),
        "name": parsed.path.lstrip("/") or "",
    }


def connect(url_from_flag: str | None = None) -> psycopg.Connection:
    env = db_env(url_from_flag)
    return psycopg.connect(
        host=env["host"],
        port=env["port"],
        dbname=env["name"],
        user=env["user"],
        password=env["password"],
    )


def parse_helper_name(helper_name: str) -> tuple[str, str]:
    match = HELPER_NAME_RE.match(helper_name)
    if match is None:
        raise SystemExit("helper name must look like schema.function")
    return match.group("schema"), match.group("name")


def decode_cli_value(raw: str) -> object:
    if raw.startswith("env:"):
        return load_secret_from_env_name(raw[4:])
    if raw.startswith("json:"):
        try:
            return json.loads(raw[5:])
        except json.JSONDecodeError as exc:
            raise SystemExit(f"invalid json argument: {exc}") from exc
    return raw


def resolve_helper_arg_types(
    connection: psycopg.Connection,
    *,
    schema_name: str,
    function_name: str,
    arg_count: int,
) -> list[str]:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT
              p.oid,
              COALESCE(
                array_agg(format_type(argument_types.type_oid, NULL) ORDER BY argument_types.ordinality)
                  FILTER (WHERE argument_types.ordinality IS NOT NULL),
                ARRAY[]::text[]
              ) AS arg_types
            FROM pg_proc AS p
            JOIN pg_namespace AS n ON n.oid = p.pronamespace
            LEFT JOIN LATERAL unnest(p.proargtypes) WITH ORDINALITY AS argument_types(type_oid, ordinality) ON true
            WHERE n.nspname = %s
              AND p.proname = %s
              AND p.pronargs = %s
            GROUP BY p.oid
            ORDER BY p.oid
            """,
            (schema_name, function_name, arg_count),
        )
        rows = cursor.fetchall()

    if not rows:
        raise SystemExit(f"helper not found for arity {arg_count}: {schema_name}.{function_name}")
    if len(rows) != 1:
        raise SystemExit(f"helper lookup is ambiguous for arity {arg_count}: {schema_name}.{function_name}")
    return list(rows[0][1])


def print_table(cursor: psycopg.Cursor, rows: list[tuple[object, ...]]) -> None:
    if cursor.description is None:
        return
    columns = [column.name for column in cursor.description]
    if not rows:
        print("no rows")
        return
    str_rows: list[list[str]] = [["" if value is None else str(value) for value in row] for row in rows]
    widths = [len(column) for column in columns]
    for row in str_rows:
        for index, cell in enumerate(row):
            widths[index] = max(widths[index], len(cell))
    print(" | ".join(column.ljust(widths[index]) for index, column in enumerate(columns)))
    print("-+-".join("-" * width for width in widths))
    for row in str_rows:
        print(" | ".join(cell.ljust(widths[index]) for index, cell in enumerate(row)))


def execute_sql(connection: psycopg.Connection, query: str, parameters: list[object] | tuple[object, ...] | None = None) -> None:
    with connection.cursor() as cursor:
        cursor.execute(query, parameters)
        rows = cursor.fetchall() if cursor.description else []
        while cursor.nextset():
            rows = cursor.fetchall() if cursor.description else []
        print_table(cursor, rows)


def render_sql(connection: psycopg.Connection, template: str, variables: dict[str, object]) -> str:
    def replace(match: re.Match[str]) -> str:
        name = match.group(1)
        if name not in variables:
            raise SystemExit(f"missing SQL variable: {name}")
        return sql.Literal(variables[name]).as_string(connection)

    return PLACEHOLDER_RE.sub(replace, template)


def read_sql_source(sql_text: str | None, sql_file_path: str | None) -> str:
    if bool(sql_text) == bool(sql_file_path):
        raise SystemExit("provide exactly one of --sql or --file")
    if sql_text is not None:
        return sql_text
    return Path(sql_file_path).read_text(encoding="utf-8")


def fail_db_error(exc: psycopg.Error) -> NoReturn:
    message = str(exc).strip()
    raise SystemExit(message or exc.__class__.__name__) from None
