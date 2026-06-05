# simplify shipped skills

## Goal

Simplify the shipped skill surface so the docs match the current architecture more closely. The repo has already pushed much of the real policy and behavior into PostgreSQL functions, schema rules, and SQL files. The user wants to replace the current split `connect` and `admin` skills with a single user-facing skill centered on two top-level usage modes: helper-script usage and custom SQL querying.

## What I already know

* The repo currently ships two end-user skill bundles under `skills/`: `agent-kb-postgres-connect` and `agent-kb-postgres-admin`.
* Each skill currently has a `SKILL.md` plus Python wrapper scripts and `scripts/sql/*.sql` files.
* The current docs already state that authorization and effective boundaries live in the database layer, not in user-supplied CLI flags.
* `connect` currently documents ordinary-user flows such as verify connection, token registration, post flow, review flow, announcements, and categories.
* `admin` currently documents account creation, registration-token management, account lifecycle, global-role changes, and announcement approval.
* The user wants to stop splitting the user-facing story into `admin` and `connect`, and instead ship one `user skill`.
* The user wants that new skill to mainly explain two things: how to use shipped helpers and how to do custom queries.
* The user wants RLS mentioned only briefly, with the assumption that the server-side setup is already trusted and safe.
* The user prefers reducing the public script surface to only two scripts: one unified helper caller and one custom SQL runner.
* The user prefers the unified helper script to dispatch by direct database helper/function name rather than by many named subcommands.
* The user does not want to keep old task-specific scripts; they should be removed rather than preserved as compatibility wrappers.

## Assumptions (temporary)

* The goal is to simplify the shipped skill documentation and the exposed mental model, not to remove underlying Python or SQL entrypoints unless needed.
* The likely direction is to keep the database as the true contract and make the skill docs less procedural.
* The new user-facing skill may coexist temporarily with old repo files during migration, but the target public story should be a single user skill.
* The target public CLI surface should be two entrypoints, not many task-specific scripts.
* The helper runner should be generic and thin, not a high-level operation catalog.
* Migration should end with the old task-specific scripts removed.

## Open Questions

* None at the moment.

## Requirements (evolving)

* Reassess whether the current shipped skills expose too many operation-level details.
* Replace the current user-facing `connect`/`admin` split with a single user-facing skill.
* Determine the right top-level structure for that single skill.
* Simplify both docs and the external mental model presented by the repo.
* Reduce the public script surface to two entrypoints: one helper caller and one custom SQL caller.
* Preserve the real database contract and avoid misleading docs.
* The single skill should primarily explain `helper usage` and `custom SQL usage`.
* Mention RLS and server-side authorization briefly, without turning the skill into a deep security explainer.
* The helper runner should accept a helper/function name directly instead of exposing many bespoke subcommands.
* Remove the old task-specific wrapper scripts instead of keeping compatibility shims.

## Acceptance Criteria (evolving)

* [ ] A clear target structure for the shipped skills is agreed.
* [ ] The intended scope of change is clear: docs plus external mental-model reshaping.
* [ ] It is clear what the two public scripts are and how users invoke each one.
* [ ] It is clear that legacy wrapper scripts are removed.

## Definition of Done (team quality bar)

* Tests added/updated (unit/integration where appropriate)
* Lint / typecheck / CI green
* Docs/notes updated if behavior changes
* Rollout/rollback considered if risky

## Out of Scope (explicit)

* Database schema redesign unless the later design explicitly requires it.
* Replacing PostgreSQL-first architecture with an app-layer API.

## Technical Notes

* Inspected: `README.md`, `docs/developer-guide.md`, `pyproject.toml`, `docker-compose.yaml`.
* Inspected skill docs: `skills/agent-kb-postgres-connect/SKILL.md`, `skills/agent-kb-postgres-admin/SKILL.md`.
* Current pattern: `SKILL.md` explains usage; Python files validate args and dispatch SQL; SQL/database layer enforces behavior.
* User selected the broader change scope: simplify docs and the external mental model together, not docs-only.
* User explicitly chose one `user skill` instead of separate `connect` and `admin` skills.
* User explicitly prefers only two public scripts: one for helper usage and one for custom SQL usage.
* User explicitly prefers helper dispatch by direct database helper/function name.
* User explicitly wants old task-specific scripts removed.

## Technical Approach

* Replace the two current public skills with one user-facing skill.
* Collapse the public script surface into exactly two entrypoints:
  * a helper runner that accepts a database helper/function name directly plus arguments
  * a custom SQL runner for inline query strings and/or SQL files
* Rewrite README and developer docs around that simpler contract.
* Keep the database as the real behavior and authorization boundary; explain RLS briefly rather than documenting many operation-specific flows.
* Remove the old task-specific Python wrappers instead of preserving migration shims.
