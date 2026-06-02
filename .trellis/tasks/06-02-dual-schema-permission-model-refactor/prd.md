# dual schema permission model refactor

## Goal

Implement the first execution phase of the dual-schema design by moving identity and authorization into `auth`, keeping business content in `app`, and tightening database security assumptions at the same time.

## Scope

* Create the `auth` schema boundary for account and grant data.
* Replace `app.principals` with `auth.accounts`.
* Introduce `auth.principal_global_roles` as the global-role grant table.
* Move board moderator grants to `auth.board_moderators`.
* Store account status inline on `auth.accounts`.
* Introduce/refactor helper functions around the agreed MVP helper set:
  * `auth.current_account_id()`
  * `auth.current_account_status()`
  * `auth.has_global_role(role_name)`
  * `auth.is_admin()`
  * `auth.is_super_admin()`
  * `auth.is_board_moderator(board_id)`
  * `auth.can_write()`
* Rewrite RLS policies to use the new helpers and grant tables.
* Include security tightening in the same task:
  * `FORCE RLS`
  * tighter `public` privileges
  * stricter helper `search_path`

## Non-Goals

* No BBS/forum model expansion.
* No data migration or backward-compatibility layer for old bootstrap data.
* No shipped admin/helper entrypoint migration or broad doc cleanup; only schema-side fixtures/tests directly needed to keep the refactor verifiable in development.
* No DDL-capability business helper design; DDL remains an operational account concern.

## Requirements

* Preserve the knowledge-base / review-board model.
* Keep the current global role set: `super_admin`, `admin`, and implicit default user behavior.
* Keep board-scoped moderation as a separate grant relation, not a content ownership concept.
* Prefer relation/grant tables for authorization over direct role columns.
* Make write eligibility depend on centralized helper logic via `auth.can_write()`.
* Accept destructive bootstrap reset for MVP development.

## Expected Files/Areas

* `postgres/init/001-agent-knowledge-base.sql`
* schema/RLS regression tests
* any SQL/bootstrap verification fixtures directly tied to the schema refactor

## Acceptance Criteria

* [ ] `auth` and `app` schema boundaries are implemented as designed.
* [ ] Identity root is renamed from principals to accounts.
* [ ] Global role checks no longer rely on a single per-account role column.
* [ ] Board moderator grants live under `auth`.
* [ ] RLS uses the new helper set, including `auth.can_write()`.
* [ ] `FORCE RLS`, `public` tightening, and helper `search_path` tightening are included.
* [ ] Verification coverage is updated for the new schema and helper contracts.

## Notes

This task is intentionally schema-first. It owns schema/bootstrap/RLS/helper-contract changes plus database-facing verification for those contracts. Operational entrypoints, docs wording migration, and broader documentation cleanup belong to the follow-up task `.trellis/tasks/06-02-management-entrypoints-docs-migration/`.
