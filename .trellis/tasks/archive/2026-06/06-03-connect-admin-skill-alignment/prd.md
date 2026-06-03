# connect/admin skill alignment

## Goal

Clarify the relationship and implementation order between the PostgreSQL `connect` skill and the `admin` skill so the repository exposes a clean base-to-extension workflow: ordinary users validate connectivity and identity through `connect`, while privileged operators use `admin` for higher-risk account and permission operations.

## What I already know

* `connect` currently verifies database connectivity, `session_user` mapping, and active account status.
* The intended `connect` scope is broader than identity-only verification: it should also cover ordinary-user actions such as posting and reviewing/commenting flows.
* For MVP, the user wants `connect` to validate both posting and comment/review flows rather than stopping at a post-only hello path.
* For MVP, the user prefers separate ordinary-user scripts rather than one all-in-one end-to-end flow.
* For `admin` MVP, the user wants both `disable` and `delete` lifecycle operations rather than stopping at `disable` only.
* `admin` currently covers account creation and board moderator assignment, but does not yet cover disable/delete lifecycle operations or global-role changes.
* Current schema uses `ON DELETE RESTRICT` from authored content back to `auth.accounts` for at least posts and review/comment records, so deleting an account while preserving authored content requires an explicit retention strategy.
* The preferred delete strategy is: reassign authored posts/comments to a retained deleted-user placeholder account, then remove the original PostgreSQL login role and original `auth.accounts` row.
* The preferred tombstone model is a single shared deleted-user placeholder account rather than per-user tombstones.
* The tombstone account should be pre-created by schema/init rather than lazily created by the delete helper.
* The user wants `connect` to be the base skill and `admin` to build on top of that base rather than acting as a peer with overlapping responsibility.
* The user wants implementation order planning first, before changing code.

## Assumptions (temporary)

* `admin` may reuse the same environment-variable contract as `connect`, but must remain file-system independent as a separately distributed skill.
* `admin` should depend on the operational contract of `connect` conceptually, not via cross-skill imports.

## Open Questions

* None currently.

## Requirements (evolving)

* Define a clear responsibility split between `connect` and `admin`.
* Define an implementation sequence that minimizes rework.
* `connect` must cover both identity verification and normal user operations.
* `connect` MVP normal-user operations must include both posting and comment/review validation.
* `connect` should ship separate small scripts for ordinary-user flows instead of one large script.
* `admin` should mention that operators are expected to run `connect` first, but this is a documentation/workflow expectation rather than a hard runtime dependency.
* `admin` MVP must include both `disable` and `delete` lifecycle operations.
* `delete` must preserve posts/comments by reassigning authored rows to a tombstone/deleted-user placeholder account before removing the original login role and account row.
* The tombstone/deleted-user placeholder account should be shared globally.
* The shared tombstone account must be provisioned in schema/init.

## Technical Approach

* Keep `connect` as the normal-user base skill with one identity-verification entrypoint and two small operational scripts.
* Keep `admin` as a separate skill that reuses the same environment-variable contract and operational assumptions, but does not import code from `connect`.
* Extend schema/init to provision one shared tombstone account used by delete flows.
* Implement delete as a controlled migration of authored content ownership to the tombstone account, followed by removal of the original login role and account row.

## Decision (ADR-lite)

**Context**: The repository needs a clean split between ordinary-user operations and privileged administration, while still supporting account deletion without destroying authored history.

**Decision**: Make `connect` the base skill for connection, identity, and ordinary-user flow validation; make `admin` the privileged companion skill for account and permission management. Preserve historical posts/comments during delete by reassigning them to one shared tombstone account provisioned at schema/init time.

**Consequences**: The two skills remain deployment-isolated and cannot share code directly, so duplicated minimal connection logic remains acceptable. Delete flows now require schema support and test coverage for tombstone reassignment, but avoid wider schema nullability changes.

## Acceptance Criteria (evolving)

* [ ] The relationship between `connect` and `admin` is documented in a way that avoids overlap.
* [ ] The implementation order is broken into concrete phases.

## Definition of Done (team quality bar)

* Tests added/updated (unit/integration where appropriate)
* Lint / typecheck / CI green
* Docs/notes updated if behavior changes
* Rollout/rollback considered if risky

## Out of Scope (explicit)

* Cross-skill shared helper libraries.
* Reworking the authorization model beyond the agreed connect/admin boundary cleanup.
* Replacing authored-content foreign keys with nullable author references.

## Technical Notes

* Existing connect entrypoint: `skills/agent-kb-postgres-connect/scripts/verify_connection.py`
* Existing admin entrypoints: `skills/agent-kb-postgres-admin/scripts/create_principal.py`, `skills/agent-kb-postgres-admin/scripts/manage_board_moderator.py`
* `postgres/init/001-united-agent.sql` currently defines authored-content foreign keys back to `auth.accounts` with `ON DELETE RESTRICT` for content preservation-sensitive tables like `app.posts.author_id` and `app.review_entries.account_id`.
