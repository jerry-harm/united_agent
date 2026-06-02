# brainstorm: double schema design merge

## Goal

Evaluate which parts of a parallel PostgreSQL RLS-native design should be merged into `united_agent`, with the explicit constraint that this project should not drift toward a traditional BBS model. The current focus is a more aggressive two-schema split and the associated security / identity / RLS implications.

## What I already know

* The current project uses a single `app` schema.
* The current identity model is direct-login PostgreSQL mapped through `app.principals.pg_login_role`.
* The current project has `super_admin`, `admin`, and `normal_user` global roles plus board-scoped moderators.
* The current project is a knowledge-base / review-board model, not a BBS, and should not move toward a posts-plus-comments forum design.
* The user wants to adopt a dual-schema architecture.
* The user prefers a more aggressive split and does not want `board_moderators` conceptually hanging under `boards` in the schema discussion.
* The user wants `board_moderators` moved into `auth` as an authorization relationship table.
* The user likes the idea of account status.
* The user wants each major follow-up item to become its own Trellis task.
* The user wants global roles represented as a grant table rather than a single role column.
* The user wants account status stored directly on `auth.accounts` for the MVP.
* The user wants to keep the current global role set: `super_admin`, `admin`, and implicit default user behavior.
* The user wants the identity root table renamed from `principals` to `accounts` in the dual-schema design.
* DDL capability should remain with operational database accounts, not be modeled as a business-user helper concern.
* The user wants `auth.can_write()` included in the MVP helper set.
* The user wants the implementation follow-up compressed into two tasks rather than many small tasks.
* The user wants `FORCE RLS`, `public` tightening, and `search_path` tightening done together with the schema/permission refactor, not postponed to a later hardening-only phase.
* The user does not want to design for data migration at this stage; destructive bootstrap reset is acceptable for now.

## Assumptions (temporary)

* `auth` will hold identity and authorization metadata.
* `app` will hold business-domain data and read/write flows for the knowledge base.
* `auth.board_moderators` will be treated as an authorization grant relation, not as board-owned business content.
* Global roles will be represented as grants, not as a single per-principal role field.
* Account status will live directly on `auth.accounts` in the MVP.
* The MVP global role set will remain aligned with the current system and will not add `global_moderator`.
* The MVP helper set should focus on identity resolution and business-permission checks, not DDL-capability checks.
* `auth.can_write()` should centralize write eligibility based on account status.
* The follow-up implementation plan should be grouped into two larger tasks.
* Database-layer safety tightening should happen during the main schema/permission refactor.
* The current stage does not require data migration planning.
* The immediate output of this task is a staged design / task breakdown, not implementation.

## Open Questions

* None currently blocking.

## Requirements (evolving)

* Keep the project aligned with the existing knowledge-base / review workflow.
* Do not merge BBS-oriented model changes such as forum-style comments as the primary interaction model.
* Move toward a dual-schema design.
* Consider adopting account status.
* Put `board_moderators` in `auth` as an authorization relation.
* Replace the single global role column with a global-role grant table under `auth`.
* Store MVP account status directly on `auth.accounts`.
* Keep the current global role set rather than adding new global moderation roles.
* Rename the current identity root object from `principals` to `accounts` in the target design.
* Keep DDL capability outside the business helper model.
* Include `auth.can_write()` in the minimum helper set.
* Break implementation follow-ups into two separate tasks.
* Fold `FORCE RLS`, `public` tightening, and `search_path` tightening into the first implementation task.
* Do not add migration/compatibility work for existing data in this phase.

## Technical Approach

* Aggressive two-schema split:
  * `auth` for identity, account state, global role grants, and board-scoped moderator grants
  * `app` for boards and knowledge-base content data
* Authorization data should consistently use grant/relation tables instead of mixing row attributes and relation tables.

### MVP object boundary

* `auth.accounts`
* `auth.principal_global_roles`
* `auth.board_moderators`
* `app.boards`
* `app.posts`
* `app.review_entries`
* `app.review_history`
* `app.tags`
* `app.post_tags`

### Planned follow-up task split

* **Task 1: dual schema + permission model refactor**
  * create `auth.accounts`, `auth.principal_global_roles`, and `auth.board_moderators`
  * rename identity references from `principals` to `accounts`
  * move account status onto `auth.accounts`
  * replace direct role-column checks with grant-based helpers
  * rewrite RLS against the new helper set
  * include `FORCE RLS`, `public` tightening, and stricter helper `search_path`
* **Task 2: management entrypoints and docs migration**
  * migrate admin tooling to the new schema layout
  * update skills, README, and spec/docs wording
  * refresh regression tests and verification coverage
  * do not implement data migration; destructive dev bootstrap reset is acceptable

### Concrete follow-up task artifacts

* `.trellis/tasks/06-02-dual-schema-permission-model-refactor/`
* `.trellis/tasks/06-02-management-entrypoints-docs-migration/`

## Decision (ADR-lite)

**Context**: The current single-schema design keeps board moderator grants under `app`, but the new direction is to separate authorization data from business content more aggressively.

**Decision**: Treat `board_moderators` as an authorization relation and move it under `auth` rather than leaving it under `app`.

**Consequences**: The schema becomes more explicit about the difference between content and permission grants, but helper functions, RLS joins, and admin tooling will all need to cross the `auth` / `app` boundary cleanly.

### Additional Decision: Global roles use grant rows

**Context**: The current schema stores a single `business_role` directly on each principal, but the new direction is to make authorization data structurally consistent.

**Decision**: Replace the single-column global role model with an `auth.principal_global_roles` grant table.

**Consequences**: Role checks become relation-based and more extensible, but existing helper functions, admin scripts, and RLS policies will need to be rewritten away from direct `business_role` column comparisons.

### Additional Decision: Account status stays inline for MVP

**Context**: The project wants account status, but also wants to keep the MVP schema small and RLS checks straightforward.

**Decision**: Store account status directly on `auth.accounts` rather than creating a separate status/history table in the MVP.

**Consequences**: Status checks remain simple and cheap inside helper functions and RLS policies, but future status history/audit requirements will require an additional table later.

### Additional Decision: Keep the current global role set

**Context**: Moving to grant-based roles creates an opportunity to add new global moderation roles, but the project does not want to drift toward a BBS-centric governance model.

**Decision**: Keep the current global role set for the MVP: `super_admin`, `admin`, and implicit default user behavior, while preserving board-scoped moderator grants separately.

**Consequences**: The authorization model stays closer to the current system and avoids premature role expansion, but any future need for cross-board moderation without `admin` powers would require a later schema/RLS extension.

### Additional Decision: Rename principals to accounts

**Context**: Moving to a dedicated `auth` schema is also a chance to make the identity model read more like an account system than a generic principal registry.

**Decision**: Rename the identity root table from `principals` to `accounts` in the target dual-schema design.

**Consequences**: The schema becomes more intuitive for status/auth flows, but helper names, foreign keys, admin tooling, and existing terminology across docs/tests will all need coordinated renames.

### Additional Decision: Keep DDL outside the business helper set

**Context**: The parallel design includes a DDL-capability helper, but the current project does not model DDL-capable platform users and already treats database-structure changes as an operational concern.

**Decision**: Keep DDL privileges attached to operational database accounts only, and do not include DDL-capability checks in the MVP business helper set.

**Consequences**: The helper layer stays focused on application-level authorization, but any future trusted schema-modifying agent model would need a separate operational design rather than extending business roles ad hoc.

## Proposed Helper Set (draft)

* `auth.current_account_id()`
* `auth.current_account_status()`
* `auth.has_global_role(role_name)`
* `auth.is_admin()`
* `auth.is_super_admin()`
* `auth.is_board_moderator(board_id)`
* `auth.can_write()`

### Additional Decision: Centralize write eligibility in `auth.can_write()`

**Context**: Account status is part of the MVP and many write policies will need to interpret it consistently.

**Decision**: Include `auth.can_write()` in the minimum helper set instead of duplicating status checks inside each write policy.

**Consequences**: RLS policies stay shorter and status semantics remain centralized, but any future distinction between different kinds of writes may require additional helper refinement.

### Additional Decision: Do safety tightening during the main refactor

**Context**: The follow-up work is being compressed into two tasks, and the user does not want core database safety tightening deferred to a separate cleanup phase.

**Decision**: Include `FORCE RLS`, `public` permission tightening, and stricter helper `search_path` rules in the main dual-schema / permission-model refactor task.

**Consequences**: The first implementation task becomes larger, but it reduces the risk of temporarily running the new model with old schema-safety assumptions.

## Acceptance Criteria (evolving)

* [ ] A clear `auth` / `app` boundary is defined.
* [ ] Mergeable versus non-mergeable ideas from the parallel design are identified.
* [ ] Upcoming implementation work is grouped into two separate tasks with explicit scope.
* [ ] The dual-schema target keeps the knowledge-base / review model and explicitly excludes BBS drift.

## Definition of Done (team quality bar)

* Tests added/updated where appropriate
* Lint / typecheck / CI green
* Docs/notes updated if behavior changes
* Rollout/rollback considered if risky

## Out of Scope (explicit)

* Implementing the schema changes in this task
* Converting the project into a traditional BBS model

## Technical Notes

* Relevant current files:
  * `postgres/init/001-agent-knowledge-base.sql`
  * `README.md`
* Relevant external comparison document discussed in chat:
  * `Agent-BBS-RLS-native-design-v0.4.md`
