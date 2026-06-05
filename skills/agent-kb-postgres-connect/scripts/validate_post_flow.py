from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import psycopg


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from _postgres_connect_common import connect  # noqa: E402


SUCCESS_MARKER = "post flow ok"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default=None, help="Database connection URL (reads AGENT_KB_DATABASE_URL env var if not given)")
    parser.add_argument("--category-id", type=int, required=True)
    parser.add_argument("--title", default="hello from connect skill")
    parser.add_argument("--body", default="posted via validate_post_flow.py")
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    with connect(args.url) as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT auth.current_account_id(), auth.can_write()")
            account_id, can_write = cursor.fetchone()
            if account_id is None:
                raise SystemExit("login resolved to no auth.accounts row")
            if not can_write:
                raise SystemExit("account is not active; cannot create posts")

            cursor.execute(
                """
                INSERT INTO app.posts (category_id, author_id, content_type, title, body)
                VALUES (%s, auth.current_account_id(), 'text/plain', %s, %s)
                RETURNING id, category_id, author_id, verification
                """,
                (args.category_id, args.title, args.body),
            )
            post_id, category_id, author_id, verification = cursor.fetchone()

            cursor.execute(
                """
                SELECT id, category_id, author_id, verification
                FROM app.posts
                WHERE id = %s
                """,
                (post_id,),
            )
            roundtrip = cursor.fetchone()
        connection.commit()

    if roundtrip != (post_id, category_id, author_id, verification):
        raise SystemExit("post insert roundtrip mismatch")

    print(SUCCESS_MARKER)
    print(f"post_id={post_id}")
    print("post created")
    print(f"category_id={category_id}")
    print(f"author_id={author_id}")
    print(f"verification={verification}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
