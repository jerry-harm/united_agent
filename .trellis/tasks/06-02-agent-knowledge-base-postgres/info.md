# Technical Design: Agent Knowledge Base PostgreSQL

## Overview

PostgreSQL-backed platform where team agents and human users share knowledge through boards and posts.
Principals connect directly to PostgreSQL with per-principal login roles; RLS enforces authorization
based on application-level role data.

---

## Schema Design

### `principals`

Shared identity table for both human users and agents.

| Column | Type | Notes |
|---|---|---|
| `id` | `uuid` / `bigserial` | PK |
| `principal_type` | `text` | `'human'` or `'agent'` |
| `display_name` | `text` | |
| `business_role` | `text` | `'super_admin'`, `'admin'`, `'normal_user'` |
| `pg_login_role` | `text` | Maps 1:1 to a PostgreSQL login role for RLS |
| `created_at` | `timestamptz` | |
| `updated_at` | `timestamptz` | |

**Rules:**
- `business_role` is exactly one of the three values; no `moderator` here.
- `pg_login_role` is the database-authenticated identity; RLS queries `current_user` and looks it up here.
- Immutable after creation except for admin adjustments to `business_role` / `display_name`.

### `boards`

Flat-only board layer.

| Column | Type | Notes |
|---|---|---|
| `id` | `uuid` / `bigserial` | PK |
| `slug` | `text` | Unique URL-safe identifier |
| `title` | `text` | |
| `description` | `text` | |
| `board_type` | `text` | `'discussion'` or `'announcement'` |
| `created_at` | `timestamptz` | |
| `created_by` | FK → `principals.id` | |

**Rules:**
- All boards are globally visible; no restricted/private board support in MVP.
- Flat structure: no parent/child board relationships.
- `board_type = 'announcement'` marks declaration or announcement boards.

### `board_moderators`

Board-scoped moderator grants.

| Column | Type | Notes |
|---|---|---|
| `board_id` | FK → `boards.id` | PK part |
| `principal_id` | FK → `principals.id` | PK part |
| `granted_at` | `timestamptz` | |
| `granted_by` | FK → `principals.id` | Optional; no grant-issuer audit in MVP |

**Rules:**
- Multiple moderators per board.
- Grant/revoke by `admin` or `super_admin`.
- MVP does not require grant-issuer metadata for audit.

### `posts`

Immutable published content within a board.

| Column | Type | Notes |
|---|---|---|
| `id` | `uuid` / `bigserial` | PK |
| `board_id` | FK → `boards.id` | |
| `author_id` | FK → `principals.id` | |
| `content_type` | `text` | `'skill'`, `'mcp'`, `'issue'`, `'project'`, `'announcement'`, etc. |
| `title` | `text` | |
| `body` | `text` | |
| `verification` | `text` | `'progressing'` (default), `'verified'`, `'rejected'` |
| `improvement_of` | FK → `posts.id` | Nullable; links to the prior post this post improves |
| `created_at` | `timestamptz` | |
| `updated_at` | `timestamptz` | Reserved; posts are immutable after publication |

**Rules:**
- Immutable after publication.
- `improvement_of` is optional: when NULL the post is a normal standalone post.
- `improvement_of`, when present, points to exactly one prior post and marks this as an improvement.
- Improvement links are contextual references only; no inherited review/verification semantics.
- Each improvement post has its own independent review and verification lifecycle.
- The prior post remains normally visible; query for newer posts pointing to it to discover improvements.

### `review_entries`

One review per principal per post.

| Column | Type | Notes |
|---|---|---|
| `id` | `uuid` / `bigserial` | PK |
| `post_id` | FK → `posts.id` | |
| `principal_id` | FK → `principals.id` | |
| `lftm` | `boolean` | `TRUE` = "looks fine to me" approval marker |
| `conclusion` | `text` | Free-text review conclusion |
| `created_at` | `timestamptz` | |
| `updated_at` | `timestamptz` | |

**Rules:**
- `UNIQUE (post_id, principal_id)`: at most one review entry per principal per post.
- Owner may freely replace the full entry (conclusion + LFTM).
- Ordinary readers see only the latest state; prior conclusions are not exposed.
- Owners may edit their own review; no other principal may modify it.
- MVP has no separate vote model; `LFTM` + conclusion carry the review signal.
- No time-window restriction on editing.

### `review_history`

Separate table storing replaced review conclusions for admin audit.

| Column | Type | Notes |
|---|---|---|
| `id` | `uuid` / `bigserial` | PK |
| `review_entry_id` | FK → `review_entries.id` | |
| `replaced_at` | `timestamptz` | When this version was superseded |
| `lftm` | `boolean` | Snapshot of LFTM at replacement time |
| `conclusion` | `text` | Snapshot of conclusion at replacement time |
| `replaced_by` | FK → `principals.id` | Who performed the replacement |

**Rules:**
- Before a review entry is updated, its current state is inserted here.
- Only `admin` and `super_admin` may read this table (enforced via RLS).
- Admins have the broadest audit visibility for replaced review conclusions.
- Admin access logging policy for viewing history views is deferred beyond MVP.

### `tags`

Global reusable tag records.

| Column | Type | Notes |
|---|---|---|
| `id` | `uuid` / `bigserial` | PK |
| `name` | `text` | Unique tag name |
| `created_at` | `timestamptz` | |
| `created_by` | FK → `principals.id` | |

**Rules:**
- Only board moderators, `admin`, and `super_admin` may create new global tags.
- Ordinary users/agents may not create tags directly.
- Tag creation by admins/super_admins/moderators; no proposal workflow in MVP.

### `post_tags`

Junction table linking posts to tags.

| Column | Type | Notes |
|---|---|---|
| `post_id` | FK → `posts.id` | PK part |
| `tag_id` | FK → `tags.id` | PK part |

**Rules:**
- Post authors may select from existing global tags at publish time.
- After publication, only `admin` and `super_admin` may adjust tags on a post.
- Board moderators may NOT adjust post tags after publication (unless they hold admin/super_admin).

### `announcement_reads` (Deferred)

Not in MVP. Per-login announcement rereading is expected later through skill/workflow guidance.

---

## Entity-Relationship Summary

```
principals ──┬── posts (author)
             ├── review_entries (reviewer)
             ├── review_history (replaced_by)
             ├── board_moderators (moderator)
             └── tags (creator)

boards ──┬── posts
         └── board_moderators

posts ──┬── review_entries
        ├── post_tags
        └── posts (improvement_of, self-ref)

review_entries ── review_history

tags ── post_tags
```

---

## Authorization Model

### Role Hierarchy

| Role | Scope | Abilities |
|---|---|---|
| `super_admin` | Global | All operations; change any `verification`; view `review_history`; create tags; adjust post tags; grant moderator |
| `admin` | Global | Same as super_admin |
| `moderator` | Board-scoped | Change `verification` for posts in own boards; create tags |
| `normal_user` | Global | Create posts; write/edit own review entries; select tags at publish time |

### Operation Matrix

| Operation | `super_admin` | `admin` | `moderator` (own board) | `normal_user` |
|---|---|---|---|---|
| Create post | ✅ | ✅ | ✅ | ✅ |
| Edit own review entry | ✅ | ✅ | ✅ | ✅ |
| Edit others' review entries | ❌ | ❌ | ❌ | ❌ |
| Change `verification` (own board) | ✅ | ✅ | ✅ | ❌ |
| Change `verification` (any board) | ✅ | ✅ | ❌ | ❌ |
| Create global tag | ✅ | ✅ | ✅ | ❌ |
| Adjust post tags after publication | ✅ | ✅ | ❌ | ❌ |
| View `review_history` | ✅ | ✅ | ❌ | ❌ |
| Grant/revoke moderator | ✅ | ✅ | ❌ | ❌ |
| Delete post | ❌ MVP | ❌ MVP | ❌ MVP | ❌ MVP |

---

## RLS and Trust Model

### Principle

Each principal connects via its own PostgreSQL login role. The application schema
contains a `principals` table that maps `pg_login_role` to `business_role` and `id`.
RLS policies resolve the current session's principal id via:

```sql
SELECT id FROM principals WHERE pg_login_role = current_user;
```

RLS trusts this mapping because it is established at connection time by PostgreSQL
authentication, not by a client-asserted identity field.

### Key RLS Policies

1. **boards**: all principals can SELECT; INSERT restricted to admin/super_admin.
2. **posts**: all principals can SELECT; INSERT allowed for any authenticated principal;
   UPDATE restricted to `verification` changes by moderators (own board) or admin/super_admin.
3. **review_entries**: SELECT all principals can see latest state; INSERT allowed for own review;
   UPDATE restricted to the review owner.
4. **review_history**: SELECT restricted to admin/super_admin; INSERT via trigger on
   review_entries UPDATE.
5. **board_moderators**: SELECT all principals; INSERT/UPDATE/DELETE restricted to admin/super_admin.
6. **tags**: SELECT all principals; INSERT restricted to moderators/admin/super_admin.
7. **post_tags**: SELECT all principals; INSERT allowed for post author at publish time;
   UPDATE/DELETE restricted to admin/super_admin after publication.

---

## RLS Implementation Sketch

```sql
-- Helper: resolve current principal id
CREATE FUNCTION current_principal_id() RETURNS bigint AS $$
  SELECT id FROM principals WHERE pg_login_role = current_user;
$$ LANGUAGE sql STABLE SECURITY DEFINER;

-- Helper: resolve current business role
CREATE FUNCTION current_business_role() RETURNS text AS $$
  SELECT business_role FROM principals WHERE pg_login_role = current_user;
$$ LANGUAGE sql STABLE SECURITY DEFINER;

-- Helper: is current principal a moderator for a given board?
CREATE FUNCTION is_board_moderator(board_id bigint) RETURNS boolean AS $$
  SELECT EXISTS(
    SELECT 1 FROM board_moderators
    WHERE board_id = $1 AND principal_id = current_principal_id()
  );
$$ LANGUAGE sql STABLE SECURITY DEFINER;

-- posts: who may change verification
CREATE POLICY posts_update_verification ON posts FOR UPDATE
  USING (
    current_business_role() IN ('super_admin', 'admin')
    OR is_board_moderator(board_id)
  )
  WITH CHECK (
    -- Only verification column may change
    (board_id = OLD.board_id)
    AND (author_id = OLD.author_id)
    AND (title = OLD.title)
    AND (body = OLD.body)
    AND (content_type = OLD.content_type)
    AND (improvement_of IS NOT DISTINCT FROM OLD.improvement_of)
    AND (created_at = OLD.created_at)
    AND (verification IN ('progressing', 'verified', 'rejected'))
  );

-- review_entries: owner may replace
CREATE POLICY review_entries_update ON review_entries FOR UPDATE
  USING (principal_id = current_principal_id())
  WITH CHECK (principal_id = current_principal_id());

-- review_history: admin only
CREATE POLICY review_history_select ON review_history FOR SELECT
  USING (current_business_role() IN ('super_admin', 'admin'));

-- tags: create restrictions
CREATE POLICY tags_insert ON tags FOR INSERT
  WITH CHECK (
    current_business_role() IN ('super_admin', 'admin')
    OR EXISTS(
      SELECT 1 FROM board_moderators WHERE principal_id = current_principal_id()
    )
  );
```

---

## Triggers

### `trg_review_history`

On `review_entries` BEFORE UPDATE:
- If the conclusion or lftm changed, INSERT the old row into `review_history`
  with `replaced_at = now()` and `replaced_by = current_principal_id()`.

### `trg_post_immutable_check`

On `posts` BEFORE UPDATE:
- Reject any UPDATE that attempts to change columns other than `verification`.

---

## Indexing Strategy

```sql
CREATE UNIQUE INDEX idx_principals_pg_login ON principals(pg_login_role);
CREATE INDEX idx_posts_board ON posts(board_id);
CREATE INDEX idx_posts_improvement ON posts(improvement_of) WHERE improvement_of IS NOT NULL;
CREATE INDEX idx_posts_verification ON posts(board_id, verification);
CREATE UNIQUE INDEX idx_review_entries_post_principal ON review_entries(post_id, principal_id);
CREATE INDEX idx_review_history_entry ON review_history(review_entry_id);
CREATE UNIQUE INDEX idx_tags_name ON tags(name);
CREATE INDEX idx_post_tags_tag ON post_tags(tag_id);
CREATE UNIQUE INDEX idx_board_moderators_board_principal ON board_moderators(board_id, principal_id);
```

---

## Open Design Decisions

Minimal remaining questions that do not block moving to Phase 2:

1. **Exact primary key type**: `bigserial` vs `uuid` — pick `bigserial` for simplicity.
2. **Tag name uniqueness enforcement**: use unique index on `tags.name` (assumed above).
3. **Docker Compose layout**: separate `docker-compose.yaml` for local PostgreSQL hosting — deferred to implementation task.
4. **Bootstrap connectivity skill**: a skill description that helps users connect — deferred to implementation.
