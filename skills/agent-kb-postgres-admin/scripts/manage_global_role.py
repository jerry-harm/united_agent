from __future__ import annotations

import argparse

from _postgres_admin_common import open_connection, require_admin, run_sql_file, sql_file


SQL_FILES = {
    "grant": sql_file("scripts/sql/manage_global_role_grant.sql"),
    "revoke": sql_file("scripts/sql/manage_global_role_revoke.sql"),
    "list": sql_file("scripts/sql/manage_global_role_list.sql"),
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=tuple(SQL_FILES))
    parser.add_argument("--account-id")
    parser.add_argument("--role-name", choices=("normal_user", "admin", "super_admin"))
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.action in {"grant", "revoke"} and not (args.account_id and args.role_name):
        raise SystemExit("--account-id and --role-name are required for grant/revoke")
    if args.action == "grant" and args.role_name == "super_admin":
        raise SystemExit("granting super_admin via the helper is not allowed; perform the change manually under direct super_admin review")

    with open_connection() as connection:
        connection.autocommit = False
        require_admin(connection, need_super_admin=True)
        connection.rollback()

    variables: dict[str, str] = {}
    if args.account_id:
        variables["account_id"] = args.account_id
    if args.role_name:
        variables["role_name"] = args.role_name

    return run_sql_file(SQL_FILES[args.action], variables)


if __name__ == "__main__":
    raise SystemExit(main())
