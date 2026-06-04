from __future__ import annotations

import argparse

from _postgres_connect_common import connect, format_identity_row, load_identity_row


SUCCESS_MARKER = "connection ok"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default=None, help="Database connection URL (reads AGENT_KB_DATABASE_URL env var if not given)")
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    with connect(args.url) as connection:
        row = load_identity_row(connection)

    if row is None:
        raise SystemExit("login resolved to no auth.accounts row")

    current_user, session_user, account_id, account_status, display_name, pg_login_role = row

    if account_status != "active":
        raise SystemExit(f"account {account_id} is not active: {account_status}")

    for line in format_identity_row((current_user, session_user, account_id, account_status, display_name, pg_login_role)):
        print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
