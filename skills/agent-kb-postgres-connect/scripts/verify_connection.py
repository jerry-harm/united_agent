from __future__ import annotations

import os

from _postgres_connect_common import connect, format_identity_row, load_identity_row


SUCCESS_MARKER = "connection ok"


def main() -> int:
    expected_login_role = os.environ.get("AGENT_KB_EXPECTED_LOGIN_ROLE")
    expected_display_name = os.environ.get("AGENT_KB_EXPECTED_DISPLAY_NAME")

    with connect() as connection:
        row = load_identity_row(connection)

    if row is None:
        raise SystemExit("login resolved to no auth.accounts row")

    current_user, session_user, account_id, account_status, display_name, pg_login_role = row

    if account_status != "active":
        raise SystemExit(f"account {account_id} is not active: {account_status}")

    if expected_login_role and pg_login_role != expected_login_role:
        raise SystemExit(f"expected pg_login_role={expected_login_role!r}, got {pg_login_role!r}")

    if expected_display_name and display_name != expected_display_name:
        raise SystemExit(f"expected display_name={expected_display_name!r}, got {display_name!r}")

    for line in format_identity_row((current_user, session_user, account_id, account_status, display_name, pg_login_role)):
        print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
