from __future__ import annotations

import argparse
import sys
from pathlib import Path

import psycopg


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from _postgres_connect_common import connect, require_env  # noqa: E402


SUCCESS_MARKER = "review flow ok"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--post-id", type=int, required=True)
    parser.add_argument("--conclusion", default="hello from connect skill")
    return parser.parse_args()


def main() -> int:
    require_env("AGENT_KB_DB_HOST")
    require_env("AGENT_KB_DB_USER")
    require_env("AGENT_KB_DB_PASSWORD")
    args = parse_args()

    with connect() as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT auth.current_account_id(), auth.can_write()")
            account_id, can_write = cursor.fetchone()
            if account_id is None:
                raise SystemExit("login resolved to no auth.accounts row")
            if not can_write:
                raise SystemExit("account is not active; cannot create reviews")

            cursor.execute(
                """
                INSERT INTO app.review_entries (post_id, account_id, lftm, conclusion)
                VALUES (%s, auth.current_account_id(), false, %s)
                ON CONFLICT (post_id, account_id) DO UPDATE
                SET conclusion = EXCLUDED.conclusion
                RETURNING id, post_id, account_id, conclusion
                """,
                (args.post_id, args.conclusion),
            )
            review_id, post_id, review_account_id, conclusion = cursor.fetchone()

            cursor.execute(
                """
                SELECT id, post_id, account_id, conclusion
                FROM app.review_entries
                WHERE id = %s
                """,
                (review_id,),
            )
            roundtrip = cursor.fetchone()
        connection.commit()

    if roundtrip != (review_id, post_id, review_account_id, conclusion):
        raise SystemExit("review insert roundtrip mismatch")

    print(SUCCESS_MARKER)
    print(f"review_entry_id={review_id}")
    print("review entry created")
    print(f"post_id={post_id}")
    print(f"account_id={review_account_id}")
    print(f"conclusion={conclusion}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
