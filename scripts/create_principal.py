from __future__ import annotations

import argparse
import os
import re

from _postgres_admin_common import run_sql_file, sql_file


SQL_FILE = sql_file("scripts/sql/create_principal.sql")
LOGIN_ROLE_RE = re.compile(r"^[a-z_][a-z0-9_]{0,62}$")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--principal-type", required=True, choices=("human", "agent"))
    parser.add_argument("--display-name", required=True)
    parser.add_argument("--business-role", required=True, choices=("normal_user", "admin"))
    parser.add_argument("--login-role", required=True)
    parser.add_argument("--new-password", default=os.environ.get("AGENT_KB_NEW_PRINCIPAL_PASSWORD", ""))
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not LOGIN_ROLE_RE.match(args.login_role):
        raise SystemExit("login role must match PostgreSQL role naming rules")
    if not args.new_password:
        raise SystemExit("provide --new-password or set AGENT_KB_NEW_PRINCIPAL_PASSWORD")

    return run_sql_file(
        SQL_FILE,
        {
            "principal_type": args.principal_type,
            "display_name": args.display_name,
            "business_role": args.business_role,
            "login_role": args.login_role,
            "new_password": args.new_password,
        },
    )


if __name__ == "__main__":
    raise SystemExit(main())
