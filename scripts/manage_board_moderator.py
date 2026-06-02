from __future__ import annotations

import argparse

from _postgres_admin_common import run_sql_file, sql_file


SQL_FILES = {
    "assign": sql_file("scripts/sql/manage_board_moderator_assign.sql"),
    "revoke": sql_file("scripts/sql/manage_board_moderator_revoke.sql"),
    "list": sql_file("scripts/sql/manage_board_moderator_list.sql"),
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("assign", "revoke", "list"))
    parser.add_argument("--board-id")
    parser.add_argument("--principal-id")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    variables: dict[str, str] = {}
    if args.action in {"assign", "revoke"}:
        if not args.board_id or not args.principal_id:
            raise SystemExit("--board-id and --principal-id are required for assign/revoke")
        variables = {
            "board_id": args.board_id,
            "principal_id": args.principal_id,
        }
    return run_sql_file(SQL_FILES[args.action], variables)


if __name__ == "__main__":
    raise SystemExit(main())
