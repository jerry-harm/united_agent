from __future__ import annotations

import argparse

import psycopg

from _agent_kb_user_common import connect, execute_sql, fail_db_error, read_sql_source, render_sql


def parse_variable(raw: str) -> tuple[str, str]:
    if "=" not in raw:
        raise SystemExit("--var must look like name=value")
    name, value = raw.split("=", 1)
    name = name.strip()
    if not name:
        raise SystemExit("--var name must not be empty")
    return name, value


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run custom SQL from an inline string or a .sql file.")
    parser.add_argument("--url", default=None, help="Database connection URL (reads AGENT_KB_DATABASE_URL env var if not given)")
    parser.add_argument("--sql")
    parser.add_argument("--file")
    parser.add_argument("--var", action="append", default=[], help="Template variable in name=value form for {{name}} placeholders")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    variables = dict(parse_variable(item) for item in args.var)
    raw_sql = read_sql_source(args.sql, args.file)

    try:
        with connect(args.url) as connection:
            sql_text = render_sql(connection, raw_sql, variables) if variables else raw_sql
            execute_sql(connection, sql_text)
            connection.commit()
    except psycopg.Error as exc:
        fail_db_error(exc)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
