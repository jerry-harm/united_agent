## Title

Database-First Function Boundaries for Fixed Write Flows

## Context

The repository already leans SQL-first. Identity, authorization, and much of the current business behavior live in PostgreSQL helpers under the `auth` and `app` schemas. Python entrypoints mostly act as operator wrappers that load environment variables, render checked-in SQL, execute statements, and print results.

The next step is to move more fixed, common write-path behavior into PostgreSQL functions so callers invoke stable database contracts instead of shipping large business SQL snippets to users. At the same time, high-flexibility read paths such as ranking, aggregation, and ad-hoc filtering should remain user-controlled SQL rather than being prematurely frozen into server-side APIs.

This design also tightens the attachment model:

- users must not upload files as standalone objects
- attachments may be reused by later posts or reviews
- identical content should deduplicate globally
- files do not have per-user ownership
- every file must be referenced by at least one post or review

## Goals

- Move fixed write workflows into PostgreSQL function contracts.
- Keep Python skill scripts as thin call layers.
- Preserve user freedom for ad-hoc read queries.
- Support multiple attachments per post and per review entry.
- Support referencing existing attachments when creating new posts or reviews.
- Deduplicate attachment content globally by `sha256`.
- Prevent normal user flows from creating long-lived unreferenced files.

## Non-Goals

- Do not function-ize ranking, aggregation, or general ad-hoc read SQL.
- Do not add per-user attachment ownership.
- Do not expose a normal user API that creates a file blob without also creating a reference from a post or review.
- Do not optimize for large binary uploads, multipart parsing, object storage, or external file-processing pipelines.

## Decision Summary

Use PostgreSQL functions as the stable API surface for fixed write flows. Keep highly customizable read queries as direct SQL.

For attachments, store globally deduplicated content blobs in a shared table and connect them to posts and review entries through separate attachment-reference tables. Normal user flows may only introduce new file content from within content-creation functions that also attach the file in the same transaction. Those same content-creation functions may also attach already-existing file blobs.

## Recommended Boundary

### Function-ize fixed write paths

Ordinary-user fixed write paths:

- create post
- create review entry
- create post with attachments
- create review entry with attachments
- register with token
- change own password

Admin fixed operations:

- create account with PostgreSQL login
- issue registration token
- reset managed account password
- disable managed account
- delete managed account
- grant global role
- revoke global role

### Keep reads user-directed

Leave these as user-authored SQL, with optional helper views only when there is a clear repeated read model:

- ranking
- aggregation
- complex filtering
- exploratory analysis
- ad-hoc listing combinations

## Data Model

### `app.file_blobs`

Global content pool for text attachments.

Suggested columns:

- `id bigint generated always as identity primary key`
- `mime_type text not null`
- `content_text text not null`
- `content_sha256 text not null`
- `size_bytes bigint not null`
- `created_at timestamptz not null default now()`

Constraints:

- `unique (content_sha256)`
- `size_bytes >= 0`
- keep the existing text-only MIME allowlist policy, or move it into a helper/function contract

Notes:

- `sha256` is the primary dedup key.
- `md5` is not needed for core correctness and should not be the canonical dedup identifier.
- File blobs are shared content objects, not user-owned assets.

### `app.post_attachments`

Attachment references for posts.

Suggested columns:

- `post_id bigint not null references app.posts(id) on delete cascade`
- `file_blob_id bigint not null references app.file_blobs(id) on delete restrict`
- `position integer not null`
- `created_at timestamptz not null default now()`

Constraints:

- `primary key (post_id, file_blob_id)` or a dedicated surrogate key if later needed
- `unique (post_id, position)`
- `position >= 0`

### `app.review_entry_attachments`

Attachment references for review entries.

Suggested columns:

- `review_entry_id bigint not null references app.review_entries(id) on delete cascade`
- `file_blob_id bigint not null references app.file_blobs(id) on delete restrict`
- `position integer not null`
- `created_at timestamptz not null default now()`

Constraints:

- `primary key (review_entry_id, file_blob_id)` or a dedicated surrogate key if later needed
- `unique (review_entry_id, position)`
- `position >= 0`

## Attachment Lifecycle Rules

### Allowed paths

Two attachment sources are valid during content creation:

1. New attachment content supplied inline with the create-post or create-review call.
2. Existing `file_blob_id` values supplied for reuse.

### Disallowed path

Normal users may not call a standalone upload function that creates an unattached file blob.

### Referential requirement

The product rule is: every file must be referenced by at least one post or review.

Practical enforcement approach:

- normal user APIs never create a blob outside a content-creation transaction
- all blob creation for normal flows happens inside `create_*_with_attachments(...)`
- attachment reference rows are inserted in the same transaction as blob creation and post/review creation
- optional maintenance checks may detect and clean up orphaned blobs if historical data or manual admin actions ever create them

This gives strong transactional enforcement without requiring brittle circular database constraints.

## Function Contracts

### Ordinary-user functions

#### `app.create_post(...)`

Purpose:

- create a post without attachments

Responsibilities:

- resolve actor identity from the live session
- enforce write permission
- validate target category and content rules
- insert the post
- return a structured result row

Suggested result shape:

- `post_id`
- `author_account_id`
- `category_id`
- `verification`
- `created_at`

#### `app.create_post_with_attachments(...)`

Purpose:

- create a post and attach zero or more files in one transaction

Responsibilities:

- do everything from `app.create_post(...)`
- accept an ordered attachment list
- for each new attachment: validate MIME, calculate `sha256`, reuse existing blob or insert a new blob
- for each existing blob reference: verify blob existence
- create `app.post_attachments` rows with stable `position`
- return the created post plus attachment metadata

#### `app.create_review_entry(...)`

Purpose:

- create a review entry without attachments

Responsibilities:

- resolve actor identity from the live session
- enforce write permission
- validate target post and review rules
- insert the review entry
- return a structured result row

#### `app.create_review_entry_with_attachments(...)`

Purpose:

- create a review entry and attach zero or more files in one transaction

Responsibilities mirror `app.create_post_with_attachments(...)`, but target `review_entries` and `review_entry_attachments`.

#### Existing user-auth functions kept as database contracts

- `auth.register_with_token(...)`
- `auth.change_own_password(...)`

These already fit the desired function-boundary direction and should remain the canonical write contracts.

### Admin functions

#### Keep or introduce canonical functions for:

- `auth.create_account_with_login(...)`
- `auth.issue_registration_token(...)`
- `auth.reset_managed_account_password(...)`
- `auth.disable_managed_account(...)`
- `auth.delete_managed_account(...)`
- `auth.grant_global_role(...)`
- `auth.revoke_global_role(...)`

Responsibilities:

- derive authority from the live session using `auth.is_admin()`, `auth.is_super_admin()`, `auth.can_manage_account(...)`, and related helpers
- enforce policy in the database rather than in Python flags
- manage PostgreSQL login side effects and cleanup inside database-side transactional logic where feasible
- return structured rows for operator-facing scripts

## Attachment Input Shape

The exact SQL type can be finalized during implementation, but the contract needs to support both inline-new and existing-reference inputs in one ordered list.

Reasonable implementation options:

1. JSONB array input
- easiest to evolve
- simplest for Python wrappers

2. Composite types plus arrays
- stronger type safety in PostgreSQL
- more ceremony in callers and migrations

Recommended choice: JSONB for the first version.

Expected element forms:

- new content
  - `kind = 'new'`
  - `filename`
  - `mime_type`
  - `content_text`

- existing blob
  - `kind = 'existing'`
  - `file_blob_id`

Functions should preserve array order into attachment `position`.

## Python Wrapper Strategy

Python scripts should become thin wrappers around stable database functions.

Allowed Python responsibilities:

- parse arguments
- load env vars
- perform cheap local validation such as missing required args
- open the database connection
- execute `SELECT app.some_function(...)` or `SELECT auth.some_function(...)`
- print rows in a predictable operator format

Disallowed Python responsibilities:

- embedding core authorization logic
- reimplementing write-path business rules already expressible in PostgreSQL
- composing large multi-step write transactions outside the database when they can be represented as one database contract

## Error Handling

Database functions should remain the source of truth for domain and permission failures.

Examples:

- invalid category or unauthorized write -> raise SQL exception from the function
- invalid MIME type -> raise SQL exception from the function
- nonexistent `file_blob_id` in an attachment reference -> raise SQL exception from the function
- policy violation in admin flows -> raise SQL exception from the function

Python wrappers should surface those errors rather than hiding or rewriting the business meaning.

## Testing Strategy

### Static tests

- schema tests for new tables and constraints
- tests that thin wrappers call stable database functions instead of shipping large inline business SQL
- tests that attachment tables and blob table exist with expected keys and uniqueness rules

### Live tests

- create post without attachments
- create post with multiple new attachments
- create post with reused existing attachment blobs
- create review entry with multiple attachments
- verify `sha256` dedup reuses blob rows while creating fresh attachment references
- verify ordering persists through `position`
- verify invalid MIME types fail
- verify nonexistent `file_blob_id` references fail
- verify normal users cannot create unattached blobs through supported flows
- verify admin fixed operations continue to enforce role boundaries through functions

## Migration Strategy

Recommended sequence:

1. Add `app.file_blobs`, `app.post_attachments`, and `app.review_entry_attachments`.
2. Add the new write functions for content creation with attachments.
3. Switch Python scripts from direct write SQL to function calls.
4. Keep read-query flexibility unchanged.
5. Remove or deprecate any standalone normal-user upload flow that creates unattached file records.
6. Add regression tests covering dedup, multiple attachments, and existing-file reuse.

## Trade-Offs

### Benefits

- clearer, stable write API surface
- centralized authorization and validation
- easier client implementations
- global content dedup for attachments
- no user-owned file model to maintain
- no normal-path orphan files

### Costs

- database function signatures become durable contracts
- attachment creation functions become more complex than plain inserts
- JSONB attachment payloads trade some type rigor for easier evolution

## Open Implementation Choices

These are intentionally narrow implementation choices, not product-level unknowns:

- whether to use `jsonb_to_recordset(...)` or a dedicated parsing helper for attachment payloads
- whether to return attachment rows nested via JSON or as a flat result set plus follow-up query
- whether admin role grant/revoke should be separate functions or one action-parameterized function

The product and architectural direction is otherwise decided by this document.

## Recommended Next Step

Write an implementation plan that starts with the ordinary-user attachment-capable write paths, then moves admin fixed operations onto the same database-function contract style, then updates wrappers and tests.
