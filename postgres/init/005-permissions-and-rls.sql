-- 共享运行时角色只能落在显式授予的 schema / 表 / 序列 / helper function 上。
GRANT USAGE ON SCHEMA auth TO PUBLIC;
GRANT USAGE ON SCHEMA auth TO united_agent_user;
GRANT USAGE ON SCHEMA app TO united_agent_user;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA auth TO united_agent_user;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA app TO united_agent_user;
GRANT SELECT, INSERT, DELETE ON ALL TABLES IN SCHEMA app TO united_agent_user;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA auth TO united_agent_user;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA app TO united_agent_user;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA auth TO united_agent_user;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA app TO united_agent_user;
REVOKE UPDATE ON app.posts FROM united_agent_user;
GRANT UPDATE (verification) ON app.posts TO united_agent_user;
REVOKE INSERT, UPDATE, DELETE ON app.file_blobs FROM united_agent_user;
REVOKE INSERT, UPDATE, DELETE ON app.post_attachments FROM united_agent_user;
REVOKE INSERT, UPDATE, DELETE ON app.review_entry_attachments FROM united_agent_user;
REVOKE UPDATE ON app.tags FROM united_agent_user;

-- 所有受管表启用 RLS，把行可见性与写授权的最终判定保留在 PostgreSQL。
ALTER TABLE auth.accounts ENABLE ROW LEVEL SECURITY;
ALTER TABLE auth.accounts FORCE ROW LEVEL SECURITY;
ALTER TABLE auth.principal_global_roles ENABLE ROW LEVEL SECURITY;
ALTER TABLE auth.principal_global_roles FORCE ROW LEVEL SECURITY;
ALTER TABLE auth.registration_tokens ENABLE ROW LEVEL SECURITY;
ALTER TABLE auth.registration_tokens FORCE ROW LEVEL SECURITY;
ALTER TABLE app.categories ENABLE ROW LEVEL SECURITY;
ALTER TABLE app.categories FORCE ROW LEVEL SECURITY;
ALTER TABLE app.posts ENABLE ROW LEVEL SECURITY;
ALTER TABLE app.posts FORCE ROW LEVEL SECURITY;
ALTER TABLE app.review_entries ENABLE ROW LEVEL SECURITY;
ALTER TABLE app.review_entries FORCE ROW LEVEL SECURITY;
ALTER TABLE app.review_history ENABLE ROW LEVEL SECURITY;
ALTER TABLE app.review_history FORCE ROW LEVEL SECURITY;
ALTER TABLE app.file_blobs ENABLE ROW LEVEL SECURITY;
ALTER TABLE app.file_blobs FORCE ROW LEVEL SECURITY;
ALTER TABLE app.post_attachments ENABLE ROW LEVEL SECURITY;
ALTER TABLE app.post_attachments FORCE ROW LEVEL SECURITY;
ALTER TABLE app.review_entry_attachments ENABLE ROW LEVEL SECURITY;
ALTER TABLE app.review_entry_attachments FORCE ROW LEVEL SECURITY;
ALTER TABLE app.tags ENABLE ROW LEVEL SECURITY;
ALTER TABLE app.tags FORCE ROW LEVEL SECURITY;
ALTER TABLE app.profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE app.profiles FORCE ROW LEVEL SECURITY;
ALTER TABLE app.post_tags ENABLE ROW LEVEL SECURITY;
ALTER TABLE app.post_tags FORCE ROW LEVEL SECURITY;

-- 账号与全局角色授权对自身可读，管理流程对 admin 可见。
CREATE POLICY accounts_select_self_or_admin ON auth.accounts
  FOR SELECT TO united_agent_user
  USING (id = auth.current_account_id() OR auth.is_admin());

-- 公开资料表：所有人可读（含 guest），author 可更新自己的 profile，admin 可插入（注册 / 建号流程）。
CREATE POLICY profiles_select_all ON app.profiles
  FOR SELECT TO united_agent_user
  USING (true);

CREATE POLICY profiles_insert_admin ON app.profiles
  FOR INSERT TO united_agent_user
  WITH CHECK (auth.can_write() AND auth.is_admin());

CREATE POLICY profiles_update_own ON app.profiles
  FOR UPDATE TO united_agent_user
  USING (auth.can_write() AND account_id = auth.current_account_id())
  WITH CHECK (auth.can_write() AND account_id = auth.current_account_id());

CREATE POLICY accounts_update_admin ON auth.accounts
  FOR UPDATE TO united_agent_user
  USING (auth.can_manage_account(id) AND NOT auth.is_guest())
  WITH CHECK (auth.can_manage_account(id) AND NOT auth.is_guest());

CREATE POLICY accounts_insert_admin ON auth.accounts
  FOR INSERT TO united_agent_user
  WITH CHECK (auth.can_write() AND auth.is_admin() AND NOT auth.is_guest());

CREATE POLICY accounts_delete_admin ON auth.accounts
  FOR DELETE TO united_agent_user
  USING (auth.can_manage_account(id) AND NOT auth.is_guest());

CREATE POLICY principal_global_roles_select_self_or_admin ON auth.principal_global_roles
  FOR SELECT TO united_agent_user
  USING (account_id = auth.current_account_id() OR auth.is_admin());

-- 全局角色授权只有 super_admin 可写。
CREATE POLICY principal_global_roles_write_super_admin ON auth.principal_global_roles
  FOR ALL TO united_agent_user
  USING (auth.can_write() AND auth.is_super_admin())
  WITH CHECK (auth.can_write() AND auth.is_super_admin());

CREATE POLICY principal_global_roles_insert_admin_normal_user ON auth.principal_global_roles
  FOR INSERT TO united_agent_user
  WITH CHECK (
    auth.can_write()
    AND NOT auth.is_guest()
    AND (
      auth.is_super_admin()
      OR (
        auth.is_admin()
        AND role_name = 'normal_user'::auth.global_role
      )
    )
  );

CREATE POLICY categories_select_all ON app.categories
  FOR SELECT TO united_agent_user
  USING (true);

-- Category 全局可读，只有 admin 可以创建或修改。
CREATE POLICY categories_insert_admin ON app.categories
  FOR INSERT TO united_agent_user
  WITH CHECK (auth.is_admin() AND auth.can_write() AND created_by = auth.current_account_id());

CREATE POLICY categories_update_admin ON app.categories
  FOR UPDATE TO united_agent_user
  USING (auth.can_write() AND auth.is_admin())
  WITH CHECK (auth.can_write() AND auth.is_admin());

CREATE POLICY categories_delete_admin ON app.categories
  FOR DELETE TO united_agent_user
  USING (auth.can_write() AND auth.is_admin());

-- Post 全局可读，作者可发布 progressing 状态，只有 admin 可改 verification 或删除。
CREATE POLICY posts_select_all ON app.posts
  FOR SELECT TO united_agent_user
  USING (true);

CREATE POLICY posts_insert_authenticated ON app.posts
  FOR INSERT TO united_agent_user
  WITH CHECK (
    auth.can_write()
    AND NOT auth.is_guest()
    AND author_id = auth.current_account_id()
    AND verification = 'progressing'
    AND (
      auth.is_admin()
      OR NOT EXISTS (
        SELECT 1
        FROM app.categories AS restricted_category
        WHERE restricted_category.id = category_id
          AND restricted_category.slug = 'announcement'
      )
    )
  );

CREATE POLICY posts_update_verification ON app.posts
  FOR UPDATE TO united_agent_user
  USING (auth.can_write() AND auth.is_admin())
  WITH CHECK (auth.can_write() AND auth.is_admin());

CREATE POLICY posts_delete_admin ON app.posts
  FOR DELETE TO united_agent_user
  USING (auth.can_write() AND auth.is_admin());

-- Review entry 全局可读，每个账号只能写自己的 review 行。
CREATE POLICY review_entries_select_all ON app.review_entries
  FOR SELECT TO united_agent_user
  USING (true);

CREATE POLICY review_entries_insert_own ON app.review_entries
  FOR INSERT TO united_agent_user
  WITH CHECK (auth.can_write() AND NOT auth.is_guest() AND account_id = auth.current_account_id());

CREATE POLICY review_entries_update_own ON app.review_entries
  FOR UPDATE TO united_agent_user
  USING (auth.can_write() AND NOT auth.is_guest() AND account_id = auth.current_account_id())
  WITH CHECK (auth.can_write() AND NOT auth.is_guest() AND account_id = auth.current_account_id());

CREATE POLICY review_entries_delete_admin ON app.review_entries
  FOR DELETE TO united_agent_user
  USING (auth.can_write() AND auth.is_admin());

CREATE POLICY review_history_select_all ON app.review_history
  FOR SELECT TO united_agent_user
  USING (true);

CREATE POLICY review_history_delete_admin ON app.review_history
  FOR DELETE TO united_agent_user
  USING (auth.can_write() AND auth.is_admin());

CREATE POLICY file_blobs_select_via_attachments ON app.file_blobs
  FOR SELECT TO united_agent_user
  USING (
    EXISTS (
      SELECT 1
      FROM app.post_attachments AS pa
      WHERE pa.file_blob_id = app.file_blobs.id
    )
    OR EXISTS (
      SELECT 1
      FROM app.review_entry_attachments AS rea
      WHERE rea.file_blob_id = app.file_blobs.id
    )
  );

CREATE POLICY post_attachments_select_all ON app.post_attachments
  FOR SELECT TO united_agent_user
  USING (true);

CREATE POLICY review_entry_attachments_select_all ON app.review_entry_attachments
  FOR SELECT TO united_agent_user
  USING (true);

CREATE POLICY tags_select_all ON app.tags
  FOR SELECT TO united_agent_user
  USING (true);

-- Tag 全局可读，只有 admin 可以创建或删除。
CREATE POLICY tags_insert_admin ON app.tags
  FOR INSERT TO united_agent_user
  WITH CHECK (
    auth.can_write()
    AND created_by = auth.current_account_id()
    AND auth.is_admin()
  );

CREATE POLICY tags_delete_admin ON app.tags
  FOR DELETE TO united_agent_user
  USING (auth.can_write() AND auth.is_admin());

CREATE POLICY post_tags_select_all ON app.post_tags
  FOR SELECT TO united_agent_user
  USING (true);

-- post tag 可由 post 作者或 admin 管理。
CREATE POLICY post_tags_insert_author_or_admin ON app.post_tags
  FOR INSERT TO united_agent_user
  WITH CHECK (
    auth.can_write()
    AND EXISTS (
      SELECT 1
      FROM app.posts AS p
      WHERE p.id = post_id
        AND (
          p.author_id = auth.current_account_id()
          OR auth.is_admin()
        )
    )
  );

CREATE POLICY post_tags_delete_author_or_admin ON app.post_tags
  FOR DELETE TO united_agent_user
  USING (
    (
      auth.can_write()
      AND auth.is_admin()
    )
    OR EXISTS (
        SELECT 1
        FROM app.posts AS p
        WHERE p.id = post_id
          AND p.author_id = auth.current_account_id()
          AND auth.can_write()
      )
  );

CREATE POLICY registration_tokens_select_admin ON auth.registration_tokens
  FOR SELECT TO united_agent_user
  USING (auth.can_write() AND auth.is_admin());

CREATE POLICY registration_tokens_insert_admin ON auth.registration_tokens
  FOR INSERT TO united_agent_user
  WITH CHECK (auth.can_write() AND auth.is_admin());

CREATE POLICY registration_tokens_update_admin ON auth.registration_tokens
  FOR UPDATE TO united_agent_user
  USING (auth.can_write() AND auth.is_admin())
  WITH CHECK (auth.can_write() AND auth.is_admin());
