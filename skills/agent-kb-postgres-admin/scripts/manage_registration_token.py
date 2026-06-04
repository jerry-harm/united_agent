from __future__ import annotations

import argparse
import secrets

from _postgres_admin_common import run_sql_file, sql_file


SQL_FILES = {
    "create": sql_file("scripts/sql/manage_registration_token_create.sql"),
    "list": sql_file("scripts/sql/manage_registration_token_list.sql"),
    "revoke": sql_file("scripts/sql/manage_registration_token_revoke.sql"),
}


def build_token() -> str:
    return secrets.token_urlsafe(24)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=tuple(SQL_FILES))
    parser.add_argument("--max-uses", type=int)
    parser.add_argument("--expires-at")
    parser.add_argument("--token-id")
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    if args.action == "create":
        if args.max_uses is None:
            raise SystemExit("--max-uses is required for create")
        token = build_token()
        run_sql_file(
            SQL_FILES[args.action],
            {
                "token": token,
                "max_uses": args.max_uses,
                "expires_at": args.expires_at,
            },
        )
        print(f"token={token}")
        return 0

    if args.action == "revoke":
        if not args.token_id:
            raise SystemExit("--token-id is required for revoke")
        return run_sql_file(SQL_FILES[args.action], {"token_id": args.token_id})

    return run_sql_file(SQL_FILES[args.action], {})


if __name__ == "__main__":
    raise SystemExit(main())
