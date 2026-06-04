from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from _postgres_connect_common import connect, load_secret_from_env_name  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--token", required=True)
    parser.add_argument("--display-name", required=True)
    parser.add_argument("--login-role", required=True)
    parser.add_argument("--principal-type", default="human", choices=("human", "agent"))
    parser.add_argument("--new-password-env", required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    token_hash = hashlib.sha256(args.token.encode("utf-8")).hexdigest()
    new_password = load_secret_from_env_name(args.new_password_env)

    with connect() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT id, principal_type, display_name, pg_login_role, account_status, remaining_uses FROM auth.register_with_token(%s, %s, %s, %s, %s)",
                (token_hash, args.principal_type, args.display_name, args.login_role, new_password),
            )
            account_id, principal_type, display_name, pg_login_role, account_status, remaining_uses = cursor.fetchone()
        connection.commit()

    print("registration ok")
    print(f"account_id={account_id}")
    print(f"principal_type={principal_type}")
    print(f"display_name={display_name}")
    print(f"pg_login_role={pg_login_role}")
    print(f"account_status={account_status}")
    print(f"remaining_uses={remaining_uses}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
