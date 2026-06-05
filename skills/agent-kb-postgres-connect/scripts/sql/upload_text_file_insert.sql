INSERT INTO app.uploaded_files (filename, uploader_account_id, mime_type, content)
VALUES ({{ filename }}, auth.current_account_id(), {{ mime_type }}, {{ content }})
RETURNING
  id,
  filename,
  uploader_account_id,
  mime_type,
  size_bytes,
  created_at,
  app.file_upload_url(id) AS file_url;
