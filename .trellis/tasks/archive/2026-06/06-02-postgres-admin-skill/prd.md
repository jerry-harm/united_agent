# brainstorm: postgres admin skill

## Goal

Create a project-distributed admin skill for privileged PostgreSQL management operations in the agent knowledge base, and likely pair it with Python helper scripts so admins can manage accounts and permissions without manually reconstructing low-level SQL each time.

## What I already know

* This repository already ships one distributed skill at `skills/agent-kb-postgres-connect/SKILL.md`.
* Existing project skill layout is `skills/<skill-name>/SKILL.md`.
* The current database skeleton lives in `postgres/init/001-agent-knowledge-base.sql`.
* The current schema already supports some privileged management operations through existing tables/functions, but the skill should be designed from the user's needed admin tasks first, then map those tasks to implementation.
* Existing privileged operations currently visible in the schema are:
  * `app.bootstrap_principal(...)` for creating principals and PostgreSQL login roles
  * direct `UPDATE` on `app.principals.business_role` by admin/super_admin
  * `INSERT` / `DELETE` on `app.board_moderators` by admin/super_admin
  * `SELECT` inspection workflows for principals, boards, and moderator assignments
* The user wants "admin" here to mean privileged database-management operations, not normal end-user workflows.
* The user wants the skill to cover all operations that are not intended for normal users.
* The user prefers Python scripts for wrapping admin operations where practical.
* The first priority for the admin skill is user/principal creation.
* For principal creation, the first version should support creating `normal_user` and `admin` accounts.
* Moderator/board-moderator management is also part of the target admin workflow.
* The skill should explicitly document what each admin level is allowed to do.
* In the skill's first version, `admin` should be treated as allowed to create only `normal_user`, while `super_admin` is required to create `admin`.
* `super_admin` should be allowed to change any global role.
* `admin` should not manage global roles; instead, `admin` should handle lower-risk operations such as granting moderator identity to normal users.
* Admin tooling should prefer reading database connection settings from environment variables.

## Assumptions (temporary)

* The skill should stay concise and mostly orchestrate existing commands/scripts rather than embed a full operations manual.
* The first version should be user-task-driven: identify the admin jobs users actually need, then implement the smallest correct support for those jobs.

## Open Questions

* None currently blocking.

## Requirements (evolving)

* Add a project-distributed PostgreSQL admin skill.
* The skill should target privileged database-management tasks only.
* The skill should be organized around user-facing admin jobs, not raw SQL primitives.
* The skill should reflect the current schema and permission model accurately.
* The first version should optimize first for creating new users/principals.
* The first version should support creating `normal_user` and `admin` principals.
* The admin workflow should also cover board moderator assignment management.
* The skill must clearly distinguish `admin` vs `super_admin` responsibilities.
* For user creation, the skill must enforce/document this policy:
  * `admin` can create `normal_user`
  * `super_admin` can create `admin`
* For role management, the skill must enforce/document this policy:
  * `super_admin` can change any global role
  * `admin` does not change global roles
  * `admin` can grant moderator assignments to normal users
* Admin tooling should prefer environment-variable-based database connection configuration.

## Technical Approach

* Add a new distributed skill at `skills/agent-kb-postgres-admin/SKILL.md`.
* Add Python helper scripts for the highest-priority admin operations, starting with principal creation.
* Keep the skill user-task-oriented: it should guide admins toward the right script or command based on intent.
* Use environment variables as the primary source of database connection settings, with explicit fallback instructions when they are missing.
* Implement a safer operational policy in the skill/scripts than the raw SQL surface currently enforces:
  * `admin` may create `normal_user`
  * `super_admin` may create `admin`
  * only `super_admin` changes global roles
  * `admin` handles lower-risk moderator assignment actions

## Decision (ADR-lite)

**Context**: The existing schema already exposes low-level SQL operations, but the user wants a practical admin experience centered on real management jobs, not database primitives.

**Decision**: Build the first version around the user-facing task of principal creation, then define the skill's privilege model explicitly and back it with Python scripts that prefer environment-based configuration.

**Consequences**: The skill will be safer and more usable than raw SQL snippets, but it may intentionally restrict some actions that the current database layer technically allows.

## Acceptance Criteria (evolving)

* [ ] The admin skill documents the current privileged management workflows accurately.

## Definition of Done (team quality bar)

* Tests added/updated where appropriate
* Docs/notes updated if behavior changes
* Distributed skill content matches current repo behavior

## Out of Scope (explicit)

* End-user posting/review/browsing workflows
* Adding new product capabilities unrelated to admin management

## Technical Notes

* Relevant files inspected:
  * `postgres/init/001-agent-knowledge-base.sql`
  * `skills/agent-kb-postgres-connect/SKILL.md`
  * `README.md`
* User guidance: design the skill from the operations users need; if some operations are easy to add, implement them instead of exposing only existing low-level actions.
* Important divergence from current raw DB capability: the first skill version should present a safer operational policy than the current unrestricted `admin`/`super_admin` SQL surface for principal creation.
