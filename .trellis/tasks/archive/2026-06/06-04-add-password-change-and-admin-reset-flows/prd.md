# add password change and admin reset flows

## Goal

Add two distinct password-management capabilities that fit the repository's PostgreSQL-login identity model: self-service password change for the current logged-in user, and admin/super_admin password reset for accounts they are already allowed to manage.

## What I already know

* Current identity is PostgreSQL-login-based: `auth.accounts.pg_login_role` maps to `session_user`.
* Account creation already creates PostgreSQL login roles via `auth.create_account_login(p_pg_login_role, p_pg_password)`.
* There is no shipped helper today for either self-service password change or admin-triggered password reset.
* Current admin boundaries already exist through `auth.can_manage_account(target_account_id)`: `admin` can manage `normal_user`; `super_admin` can additionally manage `admin`; neither can manage `super_admin`.
* Current project convention is to keep account/authorization logic in PostgreSQL helpers and expose thin Python skill-bundled wrappers.
* Current model has no app-level password table; password state lives in PostgreSQL roles.
* `connect` skill is ordinary-user scoped; `admin` skill is privileged-operator scoped.
* The user confirmed self-service password change should require the old password.
* The user confirmed admin reset should target managed accounts by `--account-id` only.
* The user wants agent-friendly non-interactive CLI flows rather than interactive password prompts.
* The user is open to dropping the old-password requirement if keeping it would block a non-interactive agent workflow.
* The user wants Windows compatibility considered; password input should therefore prefer an environment-variable-based non-interactive CLI path.
* The user confirmed there should be no password-env fallback; wrappers should require an explicit `--new-password-env ENV_NAME` style flag.

## Assumptions (temporary)

* Self-service password change should live under the `connect` skill because it is an ordinary-user capability.
* Admin reset should live under the `admin` skill because it is a privileged capability.
* The system should keep PostgreSQL as the single password authority.

## Open Questions

* None currently blocking.

## Requirements (evolving)

* Add self-service password change for the current logged-in user only.
* Add admin/super_admin password reset for managed target accounts only.
* Admin reset must target accounts by `--account-id` only.
* Both flows must support non-interactive agent/CLI usage.
* Password input should use an env-variable-based path that stays Windows-compatible.
* Password input should require an explicit env-variable-name flag such as `--new-password-env ENV_NAME`; do not add fixed fallback env names.

## Acceptance Criteria (evolving)

* [ ] The design separates self-service change from admin reset.
* [ ] The design keeps the PostgreSQL-login identity model as the single password authority.
* [ ] The design respects existing admin/super_admin account-management boundaries.

## Definition of Done (team quality bar)

* Tests added/updated (unit/integration where appropriate)
* Lint / typecheck / CI green
* Docs/notes updated if behavior changes
* Rollout/rollback considered if risky

## Out of Scope (explicit)

* OAuth / email reset / token-based recovery flows
* Introducing an app-managed password table
* User self-service reset of another account's password

## Technical Notes

* Relevant schema/helper file: `postgres/init/001-united-agent.sql`
* Relevant admin entrypoints: `skills/agent-kb-postgres-admin/scripts/*.py`
* Relevant ordinary-user entrypoints: `skills/agent-kb-postgres-connect/scripts/*.py`
* Relevant contracts: `.trellis/spec/backend/database-guidelines.md`
