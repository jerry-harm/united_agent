from __future__ import annotations

import unittest

from tests.live_postgres_helpers import ROOT, LivePostgresTestCase


class LiveContentPermissionDocumentationTest(unittest.TestCase):
    def test_readme_documents_live_content_permission_matrix_test(self) -> None:
        content = (ROOT / "docs/developer-guide.md").read_text(encoding="utf-8")

        self.assertIn("tests/test_content_permission_live_matrix.py", content)
        self.assertIn("uv run python -m unittest tests.test_content_permission_live_matrix -v", content)
        self.assertIn("python3 -m unittest tests.test_content_permission_live_matrix -v", content)
        self.assertIn("review_entries", content)
        self.assertIn("review_history", content)
        self.assertIn("tags", content)
        self.assertIn("uploaded_files", content)


class LiveContentPermissionMatrixTest(LivePostgresTestCase):
    def test_normal_user_content_read_and_write_boundaries(self) -> None:
        board_id = self.create_board(slug=self.make_board_slug("content"), title="Content Matrix Board")
        author_role = self.make_login_role("author")
        author_password = f"pw_{self.suffix}_author"
        peer_role = self.make_login_role("peer")
        peer_password = f"pw_{self.suffix}_peer"
        moderator_role = self.make_login_role("moderator")
        moderator_password = f"pw_{self.suffix}_moderator"

        for login_role, password, display_name in (
            (author_role, author_password, "Content Author"),
            (peer_role, peer_password, "Content Peer"),
            (moderator_role, moderator_password, "Tag Moderator"),
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
            board_id=board_id,
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

        is_admin, is_super_admin, can_write, is_board_moderator, status = self.fetch_role_flags(
            user=peer_role,
            password=peer_password,
            board_id=board_id,
        )
        self.assertFalse(is_admin)
        self.assertFalse(is_super_admin)
        self.assertTrue(can_write)
        self.assertFalse(is_board_moderator)
        self.assertEqual(status, "active")

        with self.connection_for(user=peer_role, password=peer_password) as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT count(*) FROM app.boards WHERE id = %s", (board_id,))
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
                    "UPDATE app.boards SET title = %s WHERE id = %s",
                    ("peer update denied", board_id),
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

        moderator_account_id = self.fetch_account_id(moderator_role)
        assign_result = self.run_manage_board_moderator(
            "assign",
            actor_user="postgres",
            actor_password="postgres",
            board_id=board_id,
            account_id=moderator_account_id,
        )
        self.assertEqual(assign_result.returncode, 0, assign_result.stderr)

        moderator_tag_name = self.make_tag_name("moderator")
        moderator_tag_id: int
        with self.connection_for(user=moderator_role, password=moderator_password) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO app.tags (name, created_by) VALUES (%s, auth.current_account_id()) RETURNING id",
                    (moderator_tag_name,),
                )
                moderator_tag_id = cursor.fetchone()[0]
                self.assertIsInstance(moderator_tag_id, int)
                cursor.execute(
                    "INSERT INTO app.post_tags (post_id, tag_id) VALUES (%s, %s)",
                    (post_id, moderator_tag_id),
                )
                cursor.execute("DELETE FROM app.post_tags WHERE post_id = %s AND tag_id = %s", (post_id, moderator_tag_id))
                self.assertEqual(cursor.rowcount, 1)
                cursor.execute("DELETE FROM app.tags WHERE id = %s", (moderator_tag_id,))
                self.assertEqual(cursor.rowcount, 1)
            connection.commit()

        admin_post_id = self.create_post(
            user=author_role,
            password=author_password,
            board_id=board_id,
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

    def test_disabled_moderator_loses_write_paths_but_not_read_visibility(self) -> None:
        board_id = self.create_board(slug=self.make_board_slug("disabled"), title="Disabled Moderator Board")
        moderator_role = self.make_login_role("disabled_moderator")
        moderator_password = f"pw_{self.suffix}_disabled_moderator"
        author_role = self.make_login_role("disabled_author")
        author_password = f"pw_{self.suffix}_disabled_author"

        for login_role, password, display_name in (
            (moderator_role, moderator_password, "Disabled Moderator"),
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

        moderator_account_id = self.fetch_account_id(moderator_role)
        assign_result = self.run_manage_board_moderator(
            "assign",
            actor_user="postgres",
            actor_password="postgres",
            board_id=board_id,
            account_id=moderator_account_id,
        )
        self.assertEqual(assign_result.returncode, 0, assign_result.stderr)

        post_id = self.create_post(
            user=author_role,
            password=author_password,
            board_id=board_id,
            title="Disabled Moderator Post",
            body="post for disabled moderator coverage",
        )

        is_admin, is_super_admin, can_write, is_board_moderator, status = self.fetch_role_flags(
            user=moderator_role,
            password=moderator_password,
            board_id=board_id,
        )
        self.assertFalse(is_admin)
        self.assertFalse(is_super_admin)
        self.assertTrue(can_write)
        self.assertTrue(is_board_moderator)
        self.assertEqual(status, "active")

        self.set_account_status(moderator_role, "disabled")

        is_admin, is_super_admin, can_write, is_board_moderator, status = self.fetch_role_flags(
            user=moderator_role,
            password=moderator_password,
            board_id=board_id,
        )
        self.assertFalse(is_admin)
        self.assertFalse(is_super_admin)
        self.assertFalse(can_write)
        self.assertTrue(is_board_moderator)
        self.assertEqual(status, "disabled")

        with self.connection_for(user=moderator_role, password=moderator_password) as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT count(*) FROM app.boards WHERE id = %s", (board_id,))
                self.assertEqual(cursor.fetchone()[0], 1)
                cursor.execute("SELECT count(*) FROM app.posts WHERE id = %s", (post_id,))
                self.assertEqual(cursor.fetchone()[0], 1)

        with self.connection_for(user=moderator_role, password=moderator_password) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "UPDATE app.posts SET verification = 'verified' WHERE id = %s RETURNING verification",
                    (post_id,),
                )
                self.assertEqual(cursor.rowcount, 0)
                self.assertIsNone(cursor.fetchone())
                connection.rollback()

        with self.connection_for(user=moderator_role, password=moderator_password) as connection:
            with connection.cursor() as cursor:
                with self.assertRaisesRegex(Exception, "row-level security"):
                    cursor.execute(
                        "INSERT INTO app.tags (name, created_by) VALUES (%s, auth.current_account_id())",
                        (self.make_tag_name("disabled-denied"),),
                    )
                connection.rollback()

        with self.connection_for(user=moderator_role, password=moderator_password) as connection:
            with connection.cursor() as cursor:
                with self.assertRaisesRegex(Exception, "row-level security"):
                    cursor.execute(
                        "INSERT INTO app.review_entries (post_id, account_id, lgtm, conclusion) VALUES (%s, auth.current_account_id(), false, %s)",
                        (post_id, "disabled write denied"),
                    )
                connection.rollback()

    def test_uploaded_file_permissions_and_constraints(self) -> None:
        board_id = self.create_board(slug=self.make_board_slug("uploads"), title="Upload Matrix Board")
        uploader_role = self.make_login_role("uploader")
        uploader_password = f"pw_{self.suffix}_uploader"
        peer_role = self.make_login_role("peer_upload")
        peer_password = f"pw_{self.suffix}_peer_upload"

        for login_role, password, display_name in (
            (uploader_role, uploader_password, "Upload Uploader"),
            (peer_role, peer_password, "Upload Peer"),
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

        uploaded_file_id = self.create_uploaded_file(
            user=uploader_role,
            password=uploader_password,
            filename="notes.txt",
            mime_type="text/plain",
            content="upload content for permission matrix",
        )

        with self.connection_for(user=peer_role, password=peer_password) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT filename, mime_type, content, app.file_upload_url(id) FROM app.uploaded_files WHERE id = %s",
                    (uploaded_file_id,),
                )
                filename, mime_type, content, file_url = cursor.fetchone()
                self.assertEqual(filename, "notes.txt")
                self.assertEqual(mime_type, "text/plain")
                self.assertEqual(content, "upload content for permission matrix")
                self.assertEqual(file_url, f"kb://uploaded-files/{uploaded_file_id}")

                cursor.execute("SELECT app.parse_uploaded_file_url(%s)", (file_url,))
                self.assertEqual(cursor.fetchone()[0], uploaded_file_id)

        post_id = self.create_post(
            user=uploader_role,
            password=uploader_password,
            board_id=board_id,
            title="Post With File URL",
            body=f"body references kb://uploaded-files/{uploaded_file_id}",
        )
        review_entry_id = self.create_review_entry(
            user=uploader_role,
            password=uploader_password,
            post_id=post_id,
            conclusion=f"review references kb://uploaded-files/{uploaded_file_id}",
        )

        with self.admin_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT body FROM app.posts WHERE id = %s", (post_id,))
                self.assertIn(f"kb://uploaded-files/{uploaded_file_id}", cursor.fetchone()[0])
                cursor.execute("SELECT conclusion FROM app.review_entries WHERE id = %s", (review_entry_id,))
                self.assertIn(f"kb://uploaded-files/{uploaded_file_id}", cursor.fetchone()[0])

        with self.connection_for(user=peer_role, password=peer_password) as connection:
            with connection.cursor() as cursor:
                cursor.execute("DELETE FROM app.uploaded_files WHERE id = %s", (uploaded_file_id,))
                self.assertEqual(cursor.rowcount, 0)
                connection.rollback()

        with self.connection_for(user=uploader_role, password=uploader_password) as connection:
            with connection.cursor() as cursor:
                with self.assertRaisesRegex(Exception, "violates check constraint"):
                    cursor.execute(
                        "INSERT INTO app.uploaded_files (filename, uploader_account_id, mime_type, content) VALUES (%s, auth.current_account_id(), %s, %s)",
                        ("bad.bin", "application/octet-stream", "bad mime should fail"),
                    )
                connection.rollback()

        with self.connection_for(user=uploader_role, password=uploader_password) as connection:
            with connection.cursor() as cursor:
                with self.assertRaisesRegex(Exception, "violates check constraint"):
                    cursor.execute(
                        "INSERT INTO app.uploaded_files (filename, uploader_account_id, mime_type, content) VALUES (%s, auth.current_account_id(), %s, %s)",
                        ("too-large.txt", "text/plain", "a" * (10 * 1024 * 1024 + 1)),
                    )
                connection.rollback()

        with self.admin_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute("DELETE FROM app.uploaded_files WHERE id = %s", (uploaded_file_id,))
                self.assertEqual(cursor.rowcount, 1)
            connection.commit()

        with self.admin_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT count(*) FROM app.uploaded_files WHERE id = %s", (uploaded_file_id,))
                self.assertEqual(cursor.fetchone()[0], 0)
                cursor.execute("SELECT body FROM app.posts WHERE id = %s", (post_id,))
                self.assertIn(f"kb://uploaded-files/{uploaded_file_id}", cursor.fetchone()[0])
