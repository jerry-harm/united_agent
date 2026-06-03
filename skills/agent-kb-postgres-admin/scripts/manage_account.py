from __future__ import annotations

import argparse

from _postgres_admin_common import open_connection, require_admin, run_sql_file, sql_file


SQL_FILES = {
    "disable": sql_file("scripts/sql/manage_account_disable.sql"),
    "delete": sql_file("scripts/sql/manage_account_delete.sql"),
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=tuple(SQL_FILES))
    parser.add_argument("--account-id", required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    with open_connection() as connection:
        connection.autocommit = False
        require_admin(connection)
        connection.rollback()

    return run_sql_file(
        SQL_FILES[args.action],
        {"account_id": args.account_id},
    )


if __name__ == "__main__":
    raise SystemExit(main())
