# design self-service password change

## Goal

Design a safe, minimal way for an existing authenticated user to change their own PostgreSQL login password in this repository's direct-login account model, without introducing an app-level password store.

## What I already know

* Current identity is PostgreSQL-login-based: `auth.accounts.pg_login_role` maps to the session login.
* Account creation currently creates PostgreSQL login roles via `auth.create_account_login(p_pg_login_role, p_pg_password)`.
* There is no shipped self-service password-change helper today.
* Existing admin tooling supports create/disable/delete/manage-role flows, but not password rotation.
* The project already centralizes authorization in PostgreSQL helper functions and uses `auth.can_write()` for write-capable actions.
* Current model does not have an application password table; password state lives in PostgreSQL roles.

## Assumptions (temporary)

* The preferred design should stay inside the current PostgreSQL-first identity model.
* A self-service change-password flow should operate on the current authenticated login only, not arbitrary target accounts.

## Open Questions

* Should MVP support only self-service password change for the current login, or also admin-triggered password reset for another account?

## Requirements (evolving)

* Users need a way to change their own password.

## Acceptance Criteria (evolving)

* [ ] The design explains how self-service password change fits the current PostgreSQL-login identity model.
* [ ] The design identifies the safest minimal operator/user surface for MVP.

## Definition of Done (team quality bar)

* Tests added/updated (unit/integration where appropriate)
* Lint / typecheck / CI green
* Docs/notes updated if behavior changes
* Rollout/rollback considered if risky

## Out of Scope (explicit)

* Introducing a separate app-managed password table unless explicitly chosen later.
* OAuth / email reset / token-based recovery flows for MVP.

## Technical Notes

* Relevant schema/helper file: `postgres/init/001-united-agent.sql`
* Relevant admin entrypoint: `skills/agent-kb-postgres-admin/scripts/manage_account.py`
* Relevant contracts: `.trellis/spec/backend/database-guidelines.md`
