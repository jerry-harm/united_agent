from __future__ import annotations

import argparse

import psycopg

from _agent_kb_user_common import connect, decode_cli_value, fail_db_error, parse_helper_name, print_table, resolve_helper_arg_types
from psycopg import sql


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Call one database helper/function directly by name. Use raw text args by default, env:ENV_NAME for secrets, json:<literal> for numbers/booleans/null/JSON."
    )
    parser.add_argument("--url", default=None, help="Database connection URL (reads AGENT_KB_DATABASE_URL env var if not given)")
    parser.add_argument("--helper", required=True, help="Helper/function name in schema.function form")
    parser.add_argument("--arg", action="append", default=[], help="Argument value; prefix with env: or json: when needed")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    schema_name, function_name = parse_helper_name(args.helper)
    values = [decode_cli_value(raw) for raw in args.arg]

    try:
        with connect(args.url) as connection:
            arg_types = resolve_helper_arg_types(
                connection,
                schema_name=schema_name,
                function_name=function_name,
                arg_count=len(values),
            )
            placeholders = [sql.SQL("%s::{}").format(sql.SQL(arg_type)) for arg_type in arg_types]
            query = sql.SQL("SELECT * FROM {}.{}({})").format(
                sql.Identifier(schema_name),
                sql.Identifier(function_name),
                sql.SQL(", ").join(placeholders),
            )

            with connection.cursor() as cursor:
                cursor.execute(query, values)
                rows = cursor.fetchall() if cursor.description else []
                print_table(cursor, rows)
            connection.commit()
    except psycopg.Error as exc:
        fail_db_error(exc)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
