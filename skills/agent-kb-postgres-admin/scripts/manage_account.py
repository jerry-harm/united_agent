from __future__ import annotations

import argparse

from _postgres_admin_common import (
    load_secret_from_env_name,
    open_connection,
    require_admin,
    run_sql_file,
    sql_file,
)


SQL_FILES = {
    "disable": sql_file("scripts/sql/manage_account_disable.sql"),
    "delete": sql_file("scripts/sql/manage_account_delete.sql"),
    "reset-password": sql_file("scripts/sql/manage_account_reset_password.sql"),
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=tuple(SQL_FILES))
    parser.add_argument("--account-id", required=True)
    parser.add_argument("--new-password-env")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    with open_connection() as connection:
        connection.autocommit = False
        require_admin(connection)
        connection.rollback()

    variables = {"account_id": args.account_id}
    if args.action == "reset-password":
        if not args.new_password_env:
            raise SystemExit("--new-password-env is required for reset-password")
        variables["new_password"] = load_secret_from_env_name(args.new_password_env)

    return run_sql_file(
        SQL_FILES[args.action],
        variables,
    )


if __name__ == "__main__":
    raise SystemExit(main())
