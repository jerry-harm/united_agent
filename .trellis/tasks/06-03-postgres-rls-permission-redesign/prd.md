# Redesign PostgreSQL RLS Permission Model

## Goal

Redesign the PostgreSQL authorization model in `postgres/init/001-united-agent.sql` and the related admin helpers/tests so the shipped RLS and management flows match the clarified product permission model for `normal_user`, `board_moderator`, `admin`, and `super_admin`.

## What I already know

* The current bootstrap schema lives in `postgres/init/001-united-agent.sql` and already uses `session_user`, helper functions, and RLS for authorization.
* `auth.can_write()` is the intended centralized write gate and must continue to block disabled accounts from mutating state.
* `super_admin` is the highest role and should inherit all `admin` capabilities.
* `super_admin` self-management does not need to be exposed through the ordinary helper flows; direct database maintenance is acceptable for granting/revoking `super_admin`.
* `ban` is out of scope; account state remains based on `active` / `disabled`.
* Delete behavior should remain hard delete, not soft delete.
* `board_moderator` should be able to manage content within their board, but not create boards or manage accounts.

## Assumptions (temporary)

* Existing live and static tests should be updated to express the new permission matrix rather than preserved verbatim.
* The admin helper scripts remain the shipped operator surface for account lifecycle, moderator assignment, and most global-role changes.
* We will preserve the current bootstrap shape unless a schema/helper change is required to express the agreed permission model safely.

## Requirements

* Keep identity resolution based on `session_user` and preserve `auth.can_write()` as the central write-eligibility gate.
* Preserve `disable` as the only account-state transition used to block future writes; do not introduce `ban`.
* `normal_user` permissions:
* Create posts.
* Cannot update or delete posts after creation.
* Can create their own review entries.
* Can update their own review entries.
* Updating a review entry must continue to write the previous version to `review_history`.
* Cannot delete their own review entries.
* Can manage tag associations (`post_tags`) for their own posts.
* `board_moderator` permissions:
* Cannot create boards.
* Can update `app.posts.verification` for posts in boards they moderate.
* Can hard-delete posts in boards they moderate.
* Can hard-delete review entries in boards they moderate.
* Can read all review history and hard-delete any review-history rows belonging to boards they moderate.
* Can create and delete global tags.
* Can manage post-tag associations for any post in boards they moderate, including posts authored by others.
* `admin` permissions:
* Can create, update, and delete boards.
* For content objects, admin management is primarily delete-oriented.
* Can update `app.posts.verification`.
* Can hard-delete posts, review entries, review history, tags, and post-tag associations.
* Can manage normal-user accounts.
* Cannot disable/delete/manage `admin` or `super_admin` accounts.
* `super_admin` permissions:
* Inherits all `admin` permissions.
* Can manage `admin` accounts.
* Can manage global roles.
* Ordinary helper flows do not need to expose `super_admin` self-management; direct database maintenance is acceptable for `super_admin` grants.
* `review_history` must be readable by all roles.
* `tags` must not support update; only create/delete should be allowed for moderator/admin/super_admin.
* `app.posts` updates must be restricted so the only editable column through ordinary role paths is `verification`.
* The final implementation should use the right mix of RLS, helper functions, triggers, and column-level grants where needed.

## Acceptance Criteria

* [ ] Static schema tests cover the updated permission model for posts, review entries, review history, tags, post tags, accounts, and global roles.
* [ ] Live authorization tests prove disabled accounts still fail write paths via `auth.can_write()`.
* [ ] Live authorization tests prove `normal_user` cannot update/delete posts and cannot delete review entries.
* [ ] Live authorization tests prove `board_moderator` can update `posts.verification`, delete in-scope posts/review entries/review history, and manage tags/post_tags within board scope.
* [ ] Live authorization tests prove `admin` can delete posts/review entries/review history/tags/post_tags and manage only normal-user accounts.
* [ ] Live authorization tests prove `super_admin` can manage `admin` accounts and global roles.
* [ ] The database only permits `app.posts.verification` updates through ordinary application-role paths.

## Definition of Done

* Tests added/updated (unit/integration where appropriate).
* Lint / typecheck / CI green.
* Docs/notes updated if behavior changes.
* Rollout/rollback considered if risky.

## Technical Approach

* Update RLS policies per table to reflect the new CRUD matrix.
* Add/adjust helper functions for board-scoped moderation checks and target-account privilege checks where raw policy expressions would be too complex.
* Preserve the review-history trigger flow for review-entry updates.
* Use column-level `UPDATE` grants and/or trigger enforcement on `app.posts` so only `verification` remains mutable.
* Keep `super_admin` grant as a database-maintenance operation rather than a helper-exposed workflow.

## Decision (ADR-lite)

**Context**: The current RLS model is close to the original MVP but diverges from the desired product permission model for moderation, content deletion, account-management boundaries, and `review_history` visibility.

**Decision**: Move to a hard-delete moderation model with role-specific CRUD boundaries, keep `disable` as the only account-state write gate, expose `review_history` reads to everyone, and reserve `super_admin` grant/self-management for direct database maintenance rather than regular helper flows.

**Consequences**: We will need schema/policy/test changes across multiple tables and helper scripts, but the resulting rules will be simpler to reason about than a soft-delete design.

## Out of Scope

* Introducing `ban` or other new account-status states.
* Introducing soft-delete columns/flows.
* Building a productized helper flow for granting `super_admin`.

## Technical Notes

* Core schema: `postgres/init/001-united-agent.sql`
* Existing admin docs/helpers: `skills/agent-kb-postgres-admin/SKILL.md`
* Relevant tests today:
* `tests/test_agent_kb_postgres_skeleton.py`
* `tests/test_board_post_live_flows.py`
* `tests/test_content_permission_live_matrix.py`
* `tests/test_moderator_permissions_live_flows.py`
* `tests/test_create_principal_live_flows.py`
* Existing helper SQL already distinguishes `admin` vs `super_admin` for account creation and global-role writes.
* Current `app.enforce_post_immutability()` trigger already enforces that only `verification` may change on posts; implementation may tighten this further with column-level grants.
