SELECT p.id, p.title, p.body, p.content_type, p.verification, p.created_at, p.author_id
FROM app.posts AS p
WHERE p.category_id = (SELECT id FROM app.categories WHERE slug = {{category_slug}})
  AND ({{show_all}} = 'true' OR p.verification = 'verified')
ORDER BY p.created_at DESC;
