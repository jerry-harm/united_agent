# Add Text File Uploads For Posts And Comments

## Goal

Add a file upload capability for text files so users can upload files and then reference the resulting file URLs inside post or comment content.

## What I already know

* The current schema stores post content in `app.posts.body` and comment/review content in `app.review_entries.conclusion`.
* There is no existing first-class upload or attachment table in `postgres/init/001-united-agent.sql`.
* Current live flows create posts by inserting `board_id`, `author_id`, `content_type`, `title`, and `body` into `app.posts`.
* Comments are currently modeled as review entries rather than a separate `comments` table.
* The user wants uploaded text files to be referenceable from post or comment content via address/URL.

## Assumptions (temporary)

* The initial scope is limited to text-like files rather than arbitrary binary uploads.
* Uploaded files should likely belong to the uploading account and need some readable URL/address format.
* Referencing a file from a post/comment may not require a rich editor; plain text URL insertion could be sufficient for MVP.

## Open Questions

* None currently.

## Requirements (evolving)

* Users can upload text files.
* Uploaded text files are publicly readable in MVP.
* MVP exposes upload capability through the database/content model first rather than requiring a dedicated UI flow.
* Uploaded files are immutable after creation; changing content requires uploading a new file.
* Normal users can upload files.
* `admin` and `super_admin` can delete files.
* `admin` and `super_admin` can still delete a file even if it is already referenced by a post or review/comment.
* Everyone can read files.
* This task should finish the database capability first.
* The corresponding skill documentation/scripts should be updated to show how to use the new upload capability after the database side is in place.
* Uploaded files produce an address that can be referenced inside content.
* Posts can include those addresses in `app.posts.body`.
* Review/comment content can include those addresses in `app.review_entries.conclusion`.
* A single post can reference multiple uploaded files.
* A single review/comment can reference multiple uploaded files.
* Each uploaded file records at least filename, uploader, upload time, and MIME type.
* File acceptance is based on MIME type only in MVP.
* Maximum upload size is 10 MB per file.

## Acceptance Criteria (evolving)

* [ ] A user can upload at least one supported text file successfully.
* [ ] The uploaded file can be read back without requiring uploader-only access.
* [ ] The system returns a stable address/URL for the uploaded file.
* [ ] The MVP upload flow can be exercised through database-native operations or project scripts without needing a UI.
* [ ] Updating an uploaded file in place is not allowed.
* [ ] A user can include that address/URL in a post body that is later stored successfully.
* [ ] A user can include that address/URL in a review/comment body that is later stored successfully.
* [ ] A user can include multiple file addresses in one post body that is later stored successfully.
* [ ] A user can include multiple file addresses in one review/comment body that is later stored successfully.
* [ ] A normal user cannot delete uploaded files.
* [ ] An `admin` or `super_admin` can delete uploaded files.
* [ ] Deleting a referenced file is still allowed for `admin` / `super_admin`, and existing references become invalid/broken addresses.
* [ ] Persisted file records include filename, uploader, upload time, and MIME type.
* [ ] Files larger than 10 MB are rejected.
* [ ] MIME type is stored and used as the MVP allow/deny input.
* [ ] Skill usage docs/scripts demonstrate how to upload a file and reference its address from post/review content.

## Definition of Done (team quality bar)

* Tests added/updated (unit/integration where appropriate)
* Lint / typecheck / CI green
* Docs/notes updated if behavior changes
* Rollout/rollback considered if risky

## Out of Scope (explicit)

* Arbitrary binary file uploads
* Final UX polish for advanced editors
* CDN / external object storage design unless required by the chosen MVP
* In-place file editing/version history for the same address
* Extension-based validation rules
* Refactoring `postgres/init/001-united-agent.sql` into smaller files for maintainability
* A general compatibility strategy for users who do not update local skill scripts while the database gains new features

## Decision (ADR-lite)

**Context**: The initial scope could have been post-only, post+comment, or upload infrastructure only. File readability, initial interaction mode, mutability, permissions, validation policy, deletion semantics, and delivery order also needed MVP choices.
**Decision**: MVP should support both posts and review/comment content, uploaded text files should be publicly readable, the first entrypoint should be database-native rather than UI-first, uploaded file contents should be immutable, normal users can upload, only `admin` / `super_admin` can delete, referenced files are still deletable and their existing references become invalid, MIME is the only file-type gate in MVP, the maximum size is 10 MB, and after the database work lands the skill should document the usage flow.
**Consequences**: The design should integrate with both `app.posts.body` and `app.review_entries.conclusion`. Read-path design can optimize for simple stable links instead of per-viewer authorization checks, implementation should focus on schema/RLS/script support before any interface work, the storage model should behave like a content snapshot rather than a mutable document, delete policies should follow the project's existing privileged-write patterns, validation remains simple enough to avoid extension-parsing complexity in the first version, the reference model must support multiple file links in a single content body, admins do not need reference-count blocking on delete, and the deliverable should include skill-side usage guidance once the DB capability exists.

## Technical Approach

Likely MVP shape:

* Add a first-class uploaded-files table in `app` schema for file content plus metadata.
* Add RLS so everyone can `SELECT`, authenticated active users can `INSERT`, and only `admin` / `super_admin` can `DELETE`.
* Expose a stable file address format derived from the stored record identity.
* Keep post/review content unchanged structurally; users reference one or more file addresses inside existing text fields.
* Do not block admin deletion based on existing content references; deleted file addresses simply stop resolving.
* Add tests around upload, read, reference, size limit, and delete permissions.
* After DB capability is in place, add skill-side usage examples/scripts so operators can exercise the flow without inventing SQL manually.

## Technical Notes

* Inspected `postgres/init/001-united-agent.sql`.
* Inspected `tests/test_board_post_live_flows.py`.
* Inspected `skills/agent-kb-postgres-connect/scripts/validate_post_flow.py`.
* Existing content model uses `app.posts` plus `app.review_entries`; there is no separate `comments` table today.
* Follow-up task requested: split `init.sql` into smaller maintainable units.
* Follow-up task requested: design for database capability evolving faster than locally cached/older skill scripts.
