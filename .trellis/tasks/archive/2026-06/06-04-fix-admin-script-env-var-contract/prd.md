# fix admin script env var contract

## Goal

Make the admin helper scripts accept the same primary runtime connection contract as the connect skill so operators do not have to split credentials into `AGENT_KB_DB_*` variables before running privileged admin flows.

## What I already know

* The user reports the current admin scripts still require split `AGENT_KB_DB_*` environment variables.
* The user explicitly does not want legacy split `AGENT_KB_DB_*` compatibility kept for admin connection loading.
* The user explicitly wants actual user-facing usage to rely on a single connection env: `DATABASE_URL`.
* `skills/agent-kb-postgres-admin/scripts/_postgres_admin_common.py` currently requires `AGENT_KB_DB_HOST`, `AGENT_KB_DB_USER`, and `AGENT_KB_DB_PASSWORD`, with optional `AGENT_KB_DB_PORT` and `AGENT_KB_DB_NAME`.
* `skills/agent-kb-postgres-admin/SKILL.md` says the preferred operational rule is to keep the canonical connection secret as `DATABASE_URL`, but also says today's helpers still read split `AGENT_KB_*` variables as a compatibility detail.
* `skills/agent-kb-postgres-connect/SKILL.md` already documents `DATABASE_URL` as the primary connection mechanism, with split `AGENT_KB_DB_*` variables as compatibility fallback.
* There is an existing admin docs test file: `tests/test_postgres_admin_tooling.py`.
* The repository currently contains duplicate copies of both postgres skills under `.agents/skills/agent-kb-postgres-connect/` and `.agents/skills/agent-kb-postgres-admin/`.

## Assumptions (temporary)

* The intended change is limited to admin helper connection loading and any docs/tests that describe that contract.

## Open Questions

* Should the duplicate `.agents/skills/agent-kb-postgres-{connect,admin}` copies be removed entirely, or just left untouched while `skills/` becomes the only supported location?

## Requirements (evolving)

* Admin helper scripts should no longer require operators to pre-split connection secrets into `AGENT_KB_DB_*` variables for normal usage.
* Admin helper scripts must not accept split `AGENT_KB_DB_*` database connection variables as a fallback path.
* User-facing admin usage must rely on `DATABASE_URL` as the only database connection env.

## Acceptance Criteria (evolving)

* [ ] Admin helper connection loading works with the intended runtime env contract.
* [ ] Admin helper connection loading fails fast when only split `AGENT_KB_DB_*` variables are provided.
* [ ] Tests and docs reflect the actual supported admin connection contract.

## Definition of Done (team quality bar)

* Tests added/updated (unit/integration where appropriate)
* Lint / typecheck / CI green
* Docs/notes updated if behavior changes
* Rollout/rollback considered if risky

## Out of Scope (explicit)

* Changing the SQL authorization model for admin actions.
* Changing connect-skill behavior unless needed for consistency in documentation/tests.

## Technical Notes

* Relevant implementation file: `skills/agent-kb-postgres-admin/scripts/_postgres_admin_common.py`
* Relevant docs: `skills/agent-kb-postgres-admin/SKILL.md`, `skills/agent-kb-postgres-connect/SKILL.md`
* Relevant tests: `tests/test_postgres_admin_tooling.py`

## Decision (ADR-lite)

**Context**: Admin helpers should no longer require split connection env vars, and the duplicate `.agents` skill copies are not meant to be supported.

**Decision**: Make admin helpers use `DATABASE_URL` only, update the shipped `skills/` docs accordingly, and remove the duplicate `.agents/skills/agent-kb-postgres-{connect,admin}` copies.

**Consequences**: This is a breaking change for any workflow still exporting split `AGENT_KB_DB_*` variables for admin flows, but it matches the user-facing contract and removes duplicate skill sources.
