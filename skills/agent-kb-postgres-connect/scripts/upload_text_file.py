from __future__ import annotations

import argparse
from pathlib import Path

from _postgres_connect_common import connect, render_sql


SUCCESS_MARKER = "upload ok"
FILE_URL_PREFIX = "file_url=kb://uploaded-files/"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Upload a text file into app.uploaded_files.")
    parser.add_argument("--url", default=None, help="Database connection URL (reads AGENT_KB_DATABASE_URL env var if not given)")
    parser.add_argument("--file", required=True, help="Path to the local text file to upload")
    parser.add_argument("--mime-type", required=True, help="MIME type stored for the uploaded file")
    parser.add_argument("--filename", default=None, help="Override stored filename (defaults to local file basename)")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    file_path = Path(args.file)
    content = file_path.read_text(encoding="utf-8")
    filename = args.filename or file_path.name

    with connect(args.url) as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT auth.current_account_id(), auth.can_write()")
            account_id, can_write = cursor.fetchone()
            if account_id is None:
                raise SystemExit("login resolved to no auth.accounts row")
            if not can_write:
                raise SystemExit("account is not active; cannot upload files")

            sql_text = render_sql(
                connection,
                "sql/upload_text_file_insert.sql",
                {
                    "filename": filename,
                    "mime_type": args.mime_type,
                    "content": content,
                },
            )
            cursor.execute(sql_text)
            file_id, stored_filename, uploader_account_id, mime_type, size_bytes, created_at, file_url = cursor.fetchone()
        connection.commit()

    print(SUCCESS_MARKER)
    print(f"file_id={file_id}")
    print(f"filename={stored_filename}")
    print(f"uploader_account_id={uploader_account_id}")
    print(f"mime_type={mime_type}")
    print(f"size_bytes={size_bytes}")
    print(f"created_at={created_at}")
    print(f"file_url={file_url}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
