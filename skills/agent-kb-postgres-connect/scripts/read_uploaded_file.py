from __future__ import annotations

import argparse

from _postgres_connect_common import connect, render_sql


SUCCESS_MARKER = "uploaded file read ok"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Read one uploaded text file by id or stable URL.")
    parser.add_argument("--url", default=None, help="Database connection URL (reads AGENT_KB_DATABASE_URL env var if not given)")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--file-id", type=int)
    group.add_argument("--file-url")
    return parser.parse_args()


def resolve_file_id(connection, file_id: int | None, file_url: str | None) -> int:
    if file_id is not None:
        return file_id
    with connection.cursor() as cursor:
        cursor.execute("SELECT app.parse_uploaded_file_url(%s)", (file_url,))
        resolved = cursor.fetchone()[0]
    if resolved is None:
        raise SystemExit("invalid uploaded file URL")
    return resolved


def main() -> int:
    args = parse_args()

    with connect(args.url) as connection:
        resolved_file_id = resolve_file_id(connection, args.file_id, args.file_url)
        sql_text = render_sql(connection, "sql/read_uploaded_file_by_id.sql", {"file_id": resolved_file_id})
        with connection.cursor() as cursor:
            cursor.execute(sql_text)
            row = cursor.fetchone()

    if row is None:
        raise SystemExit("uploaded file not found")

    file_id, filename, uploader_account_id, mime_type, size_bytes, created_at, content, file_url = row
    print(SUCCESS_MARKER)
    print(f"file_id={file_id}")
    print(f"filename={filename}")
    print(f"uploader_account_id={uploader_account_id}")
    print(f"mime_type={mime_type}")
    print(f"size_bytes={size_bytes}")
    print(f"created_at={created_at}")
    print(f"file_url={file_url}")
    print("content:")
    print(content)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
