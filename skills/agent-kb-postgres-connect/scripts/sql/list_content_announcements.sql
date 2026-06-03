SELECT p.id, p.title, p.body, p.content_type, p.verification, p.created_at, p.author_id
FROM app.posts AS p
WHERE p.board_id = (SELECT id FROM app.boards WHERE slug = {{board_slug}})
ORDER BY p.created_at DESC;
