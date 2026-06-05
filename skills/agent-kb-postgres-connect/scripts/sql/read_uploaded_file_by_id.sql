SELECT
  id,
  filename,
  uploader_account_id,
  mime_type,
  size_bytes,
  created_at,
  content,
  app.file_upload_url(id) AS file_url
FROM app.uploaded_files
WHERE id = {{ file_id }};
