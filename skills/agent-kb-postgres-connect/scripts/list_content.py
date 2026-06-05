from __future__ import annotations

import argparse
import sys

import psycopg

from _postgres_connect_common import connect, render_sql


def list_categories(connection: psycopg.Connection) -> None:
    sql_text = render_sql(connection, "sql/list_content_list_categories.sql")
    with connection.cursor() as cursor:
        cursor.execute(sql_text)
        rows = cursor.fetchall()
    if not rows:
        print("no categories found")
        return
    for row in rows:
        print(f"id={row[0]} slug={row[1]} title={row[2]} category_type={row[4]}")
        if row[3]:
            print(f"  description: {row[3]}")


def list_announcements(connection: psycopg.Connection, show_all: bool = False) -> None:
    sql_text = render_sql(
        connection,
        "sql/list_content_announcements.sql",
        {"category_slug": "announcement", "show_all": "true" if show_all else "false"},
    )
    with connection.cursor() as cursor:
        cursor.execute(sql_text)
        rows = cursor.fetchall()
    if not rows:
        print("no posts found in announcement category")
        return
    for row in rows:
        print(f"post_id={row[0]} title={row[1]} content_type={row[3]} verification={row[4]}")
        print(f"  created_at={row[5]} author_id={row[6]}")
        body_preview = (row[2] or "").replace("\n", " ")[:120]
        print(f"  body: {body_preview}...")


def main() -> int:
    parser = argparse.ArgumentParser(description="List categories or view announcement category content.")
    parser.add_argument("--url", default=None, help="Database connection URL (reads AGENT_KB_DATABASE_URL env var if not given)")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--list-categories", action="store_true", help="List all accessible categories")
    group.add_argument("--announcements", action="store_true", help="View posts in the announcement category (defaults to verified-only)")
    parser.add_argument(
        "--all",
        action="store_true",
        help="When used with --announcements: show all announcements including progressing and rejected",
    )

    args = parser.parse_args()

    try:
        with connect(args.url) as connection:
            if args.list_categories:
                list_categories(connection)
            elif args.announcements:
                list_announcements(connection, show_all=args.all)
    except Exception as ex:
        print(f"error: {ex}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
