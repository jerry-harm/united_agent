from __future__ import annotations

import json
import unittest

from tests.live_postgres_helpers import ROOT, LivePostgresTestCase


class LiveContentPermissionDocumentationTest(unittest.TestCase):
    def test_readme_documents_live_content_permission_matrix_test(self) -> None:
        content = (ROOT / "docs/developer-guide.md").read_text(encoding="utf-8")

        self.assertIn("tests/test_content_permission_live_matrix.py", content)
        self.assertIn("uv run python -m unittest tests.test_content_permission_live_matrix -v", content)
        self.assertNotIn("python3 -m unittest tests.test_content_permission_live_matrix -v", content)
        self.assertIn("review_entries", content)
        self.assertIn("review_history", content)
        self.assertIn("file_blobs", content)
        self.assertIn("post_attachments", content)
        self.assertIn("review_entry_attachments", content)
        self.assertIn("tags", content)


class LiveContentPermissionMatrixTest(LivePostgresTestCase):
    def test_normal_user_content_read_and_write_boundaries(self) -> None:
        category_id = self.create_category(slug=self.make_category_slug("content"), title="Content Matrix Category")
        author_role = self.make_login_role("author")
        author_password = f"pw_{self.suffix}_author"
        peer_role = self.make_login_role("peer")
        peer_password = f"pw_{self.suffix}_peer"

        for login_role, password, display_name in (
            (author_role, author_password, "Content Author"),
            (peer_role, peer_password, "Content Peer"),
        ):
            result = self.run_create_principal(
                actor_user="postgres",
                actor_password="postgres",
                display_name=display_name,
                global_role="normal_user",
                login_role=login_role,
                new_password=password,
            )
            self.assertEqual(result.returncode, 0, result.stderr)

        post_id = self.create_post(
            user=author_role,
            password=author_password,
            category_id=category_id,
            title="Matrix Post",
            body="content matrix body",
        )
        review_entry_id = self.create_review_entry(
            user=author_role,
            password=author_password,
            post_id=post_id,
            conclusion="first conclusion",
        )
        tag_id = self.create_tag(user="postgres", password="postgres", name=self.make_tag_name("admin-tag"))

        with self.connection_for(user=author_role, password=author_password) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "UPDATE app.review_entries SET conclusion = %s WHERE id = %s",
                    ("updated conclusion", review_entry_id),
                )
                cursor.execute(
                    "INSERT INTO app.post_tags (post_id, tag_id) VALUES (%s, %s)",
                    (post_id, tag_id),
                )
            connection.commit()

        with self.admin_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT count(*) FROM app.review_history WHERE review_entry_id = %s", (review_entry_id,))
                self.assertEqual(cursor.fetchone()[0], 1)

        is_admin, is_super_admin, can_write, status = self.fetch_role_flags(
            user=peer_role,
            password=peer_password,
        )
        self.assertFalse(is_admin)
        self.assertFalse(is_super_admin)
        self.assertTrue(can_write)
        self.assertEqual(status, "active")

        with self.connection_for(user=peer_role, password=peer_password) as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT count(*) FROM app.categories WHERE id = %s", (category_id,))
                self.assertEqual(cursor.fetchone()[0], 1)
                cursor.execute("SELECT count(*) FROM app.posts WHERE id = %s", (post_id,))
                self.assertEqual(cursor.fetchone()[0], 1)
                cursor.execute("SELECT count(*) FROM app.review_entries WHERE id = %s", (review_entry_id,))
                self.assertEqual(cursor.fetchone()[0], 1)
                cursor.execute("SELECT count(*) FROM app.tags WHERE id = %s", (tag_id,))
                self.assertEqual(cursor.fetchone()[0], 1)
                cursor.execute("SELECT count(*) FROM app.post_tags WHERE post_id = %s AND tag_id = %s", (post_id, tag_id))
                self.assertEqual(cursor.fetchone()[0], 1)
                cursor.execute("SELECT count(*) FROM app.review_history WHERE review_entry_id = %s", (review_entry_id,))
                self.assertEqual(cursor.fetchone()[0], 1)

        with self.connection_for(user=peer_role, password=peer_password) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "UPDATE app.categories SET title = %s WHERE id = %s",
                    ("peer update denied", category_id),
                )
                self.assertEqual(cursor.rowcount, 0)
                connection.rollback()

        with self.connection_for(user=peer_role, password=peer_password) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "UPDATE app.posts SET verification = 'verified' WHERE id = %s RETURNING verification",
                    (post_id,),
                )
                self.assertEqual(cursor.rowcount, 0)
                self.assertIsNone(cursor.fetchone())
                connection.rollback()

        with self.connection_for(user=peer_role, password=peer_password) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "UPDATE app.review_entries SET conclusion = %s WHERE id = %s",
                    ("peer update denied", review_entry_id),
                )
                self.assertEqual(cursor.rowcount, 0)
                cursor.execute("DELETE FROM app.posts WHERE id = %s", (post_id,))
                self.assertEqual(cursor.rowcount, 0)
                cursor.execute("DELETE FROM app.review_entries WHERE id = %s", (review_entry_id,))
                self.assertEqual(cursor.rowcount, 0)
                connection.rollback()

        with self.connection_for(user=author_role, password=author_password) as connection:
            with connection.cursor() as cursor:
                cursor.execute("DELETE FROM app.post_tags WHERE post_id = %s AND tag_id = %s", (post_id, tag_id))
                self.assertEqual(cursor.rowcount, 1)
            connection.commit()

        with self.connection_for(user=author_role, password=author_password) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO app.post_tags (post_id, tag_id) VALUES (%s, %s)",
                    (post_id, tag_id),
                )
            connection.commit()

        with self.connection_for(user=peer_role, password=peer_password) as connection:
            with connection.cursor() as cursor:
                with self.assertRaisesRegex(Exception, "row-level security"):
                    cursor.execute(
                        "INSERT INTO app.tags (name, created_by) VALUES (%s, auth.current_account_id())",
                        (self.make_tag_name("peer-denied"),),
                    )
                connection.rollback()

        admin_post_id = self.create_post(
            user=author_role,
            password=author_password,
            category_id=category_id,
            title="Admin Delete Post",
            body="admin delete coverage",
        )
        admin_review_entry_id = self.create_review_entry(
            user=author_role,
            password=author_password,
            post_id=admin_post_id,
            conclusion="admin delete review",
        )
        admin_tag_id = self.create_tag(user="postgres", password="postgres", name=self.make_tag_name("admin-delete"))
        with self.connection_for(user=author_role, password=author_password) as connection:
            with connection.cursor() as cursor:
                cursor.execute("UPDATE app.review_entries SET conclusion = %s WHERE id = %s", ("admin delete review updated", admin_review_entry_id))
                cursor.execute("INSERT INTO app.post_tags (post_id, tag_id) VALUES (%s, %s)", (admin_post_id, admin_tag_id))
            connection.commit()

        with self.admin_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute("DELETE FROM app.post_tags WHERE post_id = %s AND tag_id = %s", (admin_post_id, admin_tag_id))
                self.assertEqual(cursor.rowcount, 1)
                cursor.execute("DELETE FROM app.review_history WHERE review_entry_id = %s", (admin_review_entry_id,))
                self.assertEqual(cursor.rowcount, 1)
                cursor.execute("DELETE FROM app.review_entries WHERE id = %s", (admin_review_entry_id,))
                self.assertEqual(cursor.rowcount, 1)
                cursor.execute("DELETE FROM app.posts WHERE id = %s", (admin_post_id,))
                self.assertEqual(cursor.rowcount, 1)
                cursor.execute("DELETE FROM app.tags WHERE id = %s", (admin_tag_id,))
                self.assertEqual(cursor.rowcount, 1)
            connection.commit()

        with self.connection_for(user=peer_role, password=peer_password) as connection:
            with connection.cursor() as cursor:
                cursor.execute("DELETE FROM app.post_tags WHERE post_id = %s AND tag_id = %s", (post_id, tag_id))
                self.assertEqual(cursor.rowcount, 0)
                connection.rollback()

    def test_disabled_user_loses_write_paths_but_not_read_visibility(self) -> None:
        category_id = self.create_category(slug=self.make_category_slug("disabled"), title="Disabled User Category")
        disabled_role = self.make_login_role("disabled_user")
        disabled_password = f"pw_{self.suffix}_disabled_user"
        author_role = self.make_login_role("disabled_author")
        author_password = f"pw_{self.suffix}_disabled_author"

        for login_role, password, display_name in (
            (disabled_role, disabled_password, "Disabled User"),
            (author_role, author_password, "Disabled Author"),
        ):
            result = self.run_create_principal(
                actor_user="postgres",
                actor_password="postgres",
                display_name=display_name,
                global_role="normal_user",
                login_role=login_role,
                new_password=password,
            )
            self.assertEqual(result.returncode, 0, result.stderr)

        post_id = self.create_post(
            user=author_role,
            password=author_password,
            category_id=category_id,
            title="Disabled User Post",
            body="post for disabled user coverage",
        )

        is_admin, is_super_admin, can_write, status = self.fetch_role_flags(
            user=disabled_role,
            password=disabled_password,
        )
        self.assertFalse(is_admin)
        self.assertFalse(is_super_admin)
        self.assertTrue(can_write)
        self.assertEqual(status, "active")

        self.set_account_status(disabled_role, "disabled")

        is_admin, is_super_admin, can_write, status = self.fetch_role_flags(
            user=disabled_role,
            password=disabled_password,
        )
        self.assertFalse(is_admin)
        self.assertFalse(is_super_admin)
        self.assertFalse(can_write)
        self.assertEqual(status, "disabled")

        with self.connection_for(user=disabled_role, password=disabled_password) as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT count(*) FROM app.categories WHERE id = %s", (category_id,))
                self.assertEqual(cursor.fetchone()[0], 1)
                cursor.execute("SELECT count(*) FROM app.posts WHERE id = %s", (post_id,))
                self.assertEqual(cursor.fetchone()[0], 1)

        with self.connection_for(user=disabled_role, password=disabled_password) as connection:
            with connection.cursor() as cursor:
                with self.assertRaisesRegex(Exception, "row-level security"):
                    cursor.execute(
                        "INSERT INTO app.review_entries (post_id, account_id, lgtm, conclusion) VALUES (%s, auth.current_account_id(), false, %s)",
                        (post_id, "disabled write denied"),
                    )
                connection.rollback()

    def test_blob_and_attachment_permissions_and_visibility(self) -> None:
        category_id = self.create_category(slug=self.make_category_slug("attachments"), title="Attachment Matrix Category")
        author_role = self.make_login_role("attachment_author")
        author_password = f"pw_{self.suffix}_attachment_author"
        peer_role = self.make_login_role("attachment_peer")
        peer_password = f"pw_{self.suffix}_attachment_peer"

        for login_role, password, display_name in (
            (author_role, author_password, "Attachment Author"),
            (peer_role, peer_password, "Attachment Peer"),
        ):
            result = self.run_create_principal(
                actor_user="postgres",
                actor_password="postgres",
                display_name=display_name,
                global_role="normal_user",
                login_role=login_role,
                new_password=password,
            )
            self.assertEqual(result.returncode, 0, result.stderr)

        with self.connection_for(user=author_role, password=author_password) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT app.create_post_with_attachments(%s, %s, %s, %s, %s, %s::jsonb)
                    """,
                    (
                        category_id,
                        "text/plain",
                        "Post With Attachment",
                        "post body with attachment",
                        None,
                        json.dumps(
                            [
                                {
                                    "kind": "new",
                                    "mime_type": "text/plain",
                                    "content_text": "blob visible through post attachment",
                                }
                            ]
                        ),
                    ),
                )
                post_id = cursor.fetchone()[0]
                cursor.execute(
                    """
                    SELECT pa.file_blob_id
                    FROM app.post_attachments AS pa
                    WHERE pa.post_id = %s
                    ORDER BY pa.position
                    """,
                    (post_id,),
                )
                post_blob_id = cursor.fetchone()[0]
                cursor.execute(
                    """
                    SELECT app.create_review_entry_with_attachments(%s, %s, %s, %s::jsonb)
                    """,
                    (
                        post_id,
                        False,
                        "review with attachment",
                        json.dumps(
                            [
                                {
                                    "kind": "new",
                                    "mime_type": "text/markdown",
                                    "content_text": "blob visible through review attachment",
                                }
                            ]
                        ),
                    ),
                )
                review_entry_id = cursor.fetchone()[0]
                cursor.execute(
                    """
                    SELECT rea.file_blob_id
                    FROM app.review_entry_attachments AS rea
                    WHERE rea.review_entry_id = %s
                    ORDER BY rea.position
                    """,
                    (review_entry_id,),
                )
                review_blob_id = cursor.fetchone()[0]
            connection.commit()

        with self.admin_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT app.ensure_file_blob(%s, %s)", ("text/plain", "orphan blob not attached anywhere"))
                orphan_blob_id = cursor.fetchone()[0]
            connection.commit()
        self.created_file_blob_ids.add(orphan_blob_id)

        with self.connection_for(user=peer_role, password=peer_password) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT mime_type, content_text FROM app.file_blobs WHERE id = %s",
                    (post_blob_id,),
                )
                mime_type, content = cursor.fetchone()
                self.assertEqual(mime_type, "text/plain")
                self.assertEqual(content, "blob visible through post attachment")
                cursor.execute(
                    "SELECT mime_type, content_text FROM app.file_blobs WHERE id = %s",
                    (review_blob_id,),
                )
                self.assertEqual(cursor.fetchone(), ("text/markdown", "blob visible through review attachment"))
                cursor.execute(
                    "SELECT count(*) FROM app.post_attachments WHERE post_id = %s AND file_blob_id = %s",
                    (post_id, post_blob_id),
                )
                self.assertEqual(cursor.fetchone()[0], 1)
                cursor.execute(
                    "SELECT count(*) FROM app.review_entry_attachments WHERE review_entry_id = %s AND file_blob_id = %s",
                    (review_entry_id, review_blob_id),
                )
                self.assertEqual(cursor.fetchone()[0], 1)
                cursor.execute("SELECT count(*) FROM app.file_blobs WHERE id = %s", (orphan_blob_id,))
                self.assertEqual(cursor.fetchone()[0], 0)

        def assert_direct_write_denied(user: str, password: str, sql_text: str, params: tuple[object, ...]) -> None:
            with self.connection_for(user=user, password=password) as connection:
                with connection.cursor() as cursor:
                    with self.assertRaisesRegex(Exception, "permission denied|row-level security"):
                        cursor.execute(sql_text, params)
                    connection.rollback()

        assert_direct_write_denied(
            author_role,
            author_password,
            "INSERT INTO app.file_blobs (mime_type, content_text, content_sha256) VALUES (%s, %s, %s)",
            ("text/plain", "direct blob insert denied", "manual-sha-not-allowed"),
        )
        assert_direct_write_denied(
            author_role,
            author_password,
            "INSERT INTO app.post_attachments (post_id, file_blob_id, position) VALUES (%s, %s, %s)",
            (post_id, post_blob_id, 99),
        )
        assert_direct_write_denied(
            peer_role,
            peer_password,
            "DELETE FROM app.post_attachments WHERE post_id = %s AND file_blob_id = %s",
            (post_id, post_blob_id),
        )
        assert_direct_write_denied(
            peer_role,
            peer_password,
            "DELETE FROM app.review_entry_attachments WHERE review_entry_id = %s AND file_blob_id = %s",
            (review_entry_id, review_blob_id),
        )
        assert_direct_write_denied(
            peer_role,
            peer_password,
            "DELETE FROM app.file_blobs WHERE id = %s",
            (post_blob_id,),
        )


if __name__ == "__main__":
    unittest.main()
