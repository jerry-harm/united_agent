# Document design philosophy and principles

## Goal

Create a document that clearly explains the project's design thinking and core principles, so readers can understand why this repository is database-first, what boundaries it deliberately keeps, and how those choices guide future work.

## What I already know

* The repository delivers a PostgreSQL-centered system rather than a partial backend waiting for a UI or API.
* Current deliverables include database bootstrap, permission model, lightweight management scripts, distributable skills, and tests protecting those contracts.
* The current system boundary is explicit: no Web UI, no application API, and PostgreSQL itself is the deployment unit.
* Existing README already explains system positioning, repository structure, runtime model, and schema relationships.
* The primary audience is maintainers.
* The document needs to cover the current `auth` logic and the design of user operation flows.
* Current auth model is centered on `auth.accounts`, `auth.principal_global_roles`, and `auth.board_moderators`.
* Identity resolution maps PostgreSQL login to application account through `session_user -> auth.accounts.pg_login_role`.
* Write-capable paths are gated by `auth.can_write()`, while privilege checks are split between global roles and board-scoped moderator grants.
* Current user operation logic includes admin-only board creation, authenticated post creation, moderator/admin verification updates, and direct-SQL-first authorization validation.

## Assumptions (temporary)

* The new document should expand on README-level positioning rather than replace README.
* The document is meant for maintainers and future contributors who need to understand architectural intent before changing schema, auth, or user-facing operation flows.
* The document should be written in Chinese to match the existing README tone.

## Open Questions

* None currently.

## Requirements (evolving)

* Explain the project's design thought process and guiding principles in detail.
* Stay consistent with the current repository positioning described in README.
* Explain the current `auth` logic, including identity mapping, global roles, board moderator grants, and the role of RLS/helpers.
* Explain the design of user operation logic, including who can create boards, publish posts, and change verification state.
* Help maintainers understand not just what the current rules are, but why the rules are implemented inside PostgreSQL.
* Organize the document principle-first, then map those principles onto auth and operation flows.
* Keep the depth at the philosophy/concept layer rather than turning the document into a line-by-line schema or SQL reference.
* Deliver the result as a standalone document rather than folding the full content into `README.md`.

## Acceptance Criteria (evolving)

* [ ] The document explains why the system is database-first.
* [ ] The document explains the intentional system boundary and what is out of scope.
* [ ] The document describes the core design principles in a way future contributors can use.
* [ ] The document explains the current auth design in a way maintainers can reason about safely changing it.
* [ ] The document explains the main user operation flows and their authorization boundaries.
* [ ] The document stays principle-oriented and does not collapse into low-level implementation commentary.

## Definition of Done (team quality bar)

* Tests added/updated (unit/integration where appropriate)
* Lint / typecheck / CI green
* Docs/notes updated if behavior changes
* Rollout/rollback considered if risky

## Out of Scope (explicit)

* Implementing new runtime behavior
* Rewriting the existing README unless the document work proves it necessary

## Technical Notes

* Existing context source: `README.md`
* Key implementation source: `postgres/init/001-united-agent.sql`
* Related operational SQL: `scripts/sql/create_principal.sql`, `scripts/sql/manage_board_moderator_assign.sql`, `scripts/sql/manage_board_moderator_revoke.sql`, `scripts/sql/manage_board_moderator_list.sql`
* Task directory: `.trellis/tasks/06-03-design-philosophy-doc/`
* Confirmed structure direction: principle-first.
* Confirmed depth: philosophy layer, not full low-level design spec.
* Confirmed delivery shape: standalone document.

## Technical Approach

Write a standalone Chinese document for maintainers that starts from system principles, then maps those principles to the current auth model and user operation logic. The document should explain why PostgreSQL is the system boundary, why auth is resolved from database login identity, why authorization lives in helpers plus RLS, and how those ideas show up in concrete flows like account mapping, board creation, post publishing, and verification updates.

## Decision (ADR-lite)

**Context**: Maintainers need a shared explanation of the system's design intent, especially around auth and user operation logic, but the repository currently has README-level positioning rather than a dedicated philosophy document.

**Decision**: Create a standalone, principle-first Chinese document aimed at maintainers. Keep it at the philosophy/concept layer, while still covering the current auth logic and core user operation flows.

**Consequences**: The document will be easier to read as a design rationale artifact and safer for onboarding, but it will intentionally avoid becoming a low-level SQL reference. README can later link to it rather than absorbing all of its content.
