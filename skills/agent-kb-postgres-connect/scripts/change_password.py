from __future__ import annotations

import argparse
import sys

from _postgres_connect_common import connect, load_secret_from_env_name


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default=None, help="Database connection URL (reads AGENT_KB_DATABASE_URL env var if not given)")
    parser.add_argument("--new-password-env", required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    new_password = load_secret_from_env_name(args.new_password_env)
    try:
        with connect(args.url) as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT auth.change_own_password(%s)", (new_password,))
                changed_role = cursor.fetchone()[0]
            connection.commit()
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    print("password changed")
    print(f"pg_login_role={changed_role}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
