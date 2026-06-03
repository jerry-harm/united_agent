# Improve Connect Skill

## Goal

Improve `skills/agent-kb-postgres-connect/SKILL.md` so the ordinary-user connection flow is easier to use, the embedded Python path is not overly long in the main skill body, and the skill covers the missing connect/verification steps users actually need.

## What I already know

* The user thinks the Python code in the connect skill is too long.
* The user thinks the connect skill's functionality is still incomplete.
* The user explicitly wants this turned into a skill-bundled connect script.
* The user explicitly wants the missing user-side connection scripts and skill instructions filled in.
* The user explicitly wants real integration tests for the scripts.
* The user prefers the skill documentation to recommend `uv` for Python execution/setup where appropriate.
* The user wants a root-level `uv` dependency manifest / dependency table for the repo.
* The current connect skill lives at `skills/agent-kb-postgres-connect/SKILL.md`.
* The current connect skill is 141 lines and includes one inline Python heredoc block used to connect, query `auth.accounts`, and verify the mapped identity.
* The current admin skill lives at `skills/agent-kb-postgres-admin/SKILL.md` and already uses a narrower main document plus skill-bundled scripts for operational flows.
* Current repository tests only assert that the connect skill documents the Python/`psycopg` path and its ordinary-user boundary; they do not assert bundled connect scripts or live user-side verification flows.
* `README.md` currently describes the connect skill as covering Python + `psycopg` connection and identity verification, but not richer troubleshooting or reusable helper entrypoints.
* Backend specs require thin Python entrypoints, skill-bundled helper scripts for distributed usage, and regression/integration tests when operator workflows change.

## Assumptions (temporary)

* The connect skill should stay scoped to ordinary-user connection and identity verification, not privileged account creation.
* A shorter main `SKILL.md` should come from moving the heredoc flow into a bundled Python script, not from dropping the Python/`psycopg` path.
* The missing functionality is user-side connection usability and verification coverage, not privileged admin operations.

## Open Questions

* None currently blocking.

## Requirements (evolving)

* Keep `agent-kb-postgres-connect` focused on ordinary-user connection and identity verification.
* Replace the long inline heredoc-first flow with one or more skill-bundled Python scripts under `skills/agent-kb-postgres-connect/scripts/`.
* Keep the Python entrypoint thin and aligned with repo conventions.
* The bundled connect flow must let a user prove:
* the database credentials connect successfully
* the live session resolves to the expected `auth.accounts` row
* the resolved account is active
* optional expected-value checks can validate login role and display name
* The skill documentation must explain how to run the bundled script, what inputs are required, what success looks like, and what failure boundaries mean.
* The skill documentation should recommend `uv` as the preferred Python setup/run path, while staying workable for plain `python3` users.
* Add real integration coverage against a running PostgreSQL instance for the bundled connect script behavior.
* Update contract tests and README text so shipped docs match the new script-based connect flow.
* Add a root-level `pyproject.toml` so `uv` can manage the repository's Python dependencies.

## Acceptance Criteria (evolving)

* [ ] The connect skill keeps a clear boundary from the admin skill.
* [ ] `skills/agent-kb-postgres-connect/SKILL.md` documents a skill-bundled script instead of relying on a long inline heredoc as the main execution path.
* [ ] `skills/agent-kb-postgres-connect/scripts/` contains the user-side connection/identity verification entrypoint needed by the skill.
* [ ] The bundled script succeeds for a valid mapped account and emits enough output to confirm the connected identity.
* [ ] The bundled script fails clearly for at least unmapped or inactive-account conditions.
* [ ] Static contract tests are updated for the new skill/script wording and file layout.
* [ ] A live PostgreSQL integration test exercises the shipped connect script end-to-end.
* [ ] README and related docs match the final script-based workflow.
* [ ] The skill docs prefer `uv` in setup or invocation examples.
* [ ] The repository root contains a `pyproject.toml` dependency table suitable for `uv`.

## Definition of Done (team quality bar)

* Tests added/updated (unit/integration where appropriate)
* Lint / typecheck / CI green
* Docs/notes updated if behavior changes
* Rollout/rollback considered if risky

## Out of Scope (explicit)

* Turning the connect skill into a privileged admin or account-creation skill
* Broad PostgreSQL operations unrelated to connection and identity verification
* Replacing the admin skill or moving privileged workflows into the connect skill

## Technical Notes

* Inspected: `skills/agent-kb-postgres-connect/SKILL.md`
* Inspected: `skills/agent-kb-postgres-admin/SKILL.md`
* Inspected: `tests/test_agent_kb_postgres_skeleton.py`
* Inspected: `tests/test_board_post_live_flows.py`
* Inspected: `README.md`
* Inspected: `.trellis/spec/backend/index.md`
* Inspected: `.trellis/spec/backend/directory-structure.md`
* Inspected: `.trellis/spec/backend/quality-guidelines.md`

## Technical Approach

Add a distributed ordinary-user helper under `skills/agent-kb-postgres-connect/scripts/`, keep the CLI thin and environment-driven, shorten the main skill document to usage + boundary + troubleshooting, recommend `uv` as the preferred Python path, and verify the shipped path with both static contract tests and a live PostgreSQL integration test.

## Decision (ADR-lite)

**Context**: The current connect skill is correct in boundary but too bulky in the main document and does not ship a reusable user-side script.

**Decision**: Follow the same distribution pattern as the admin skill: move executable connect/identity verification behavior into a bundled Python script and keep `SKILL.md` focused on when to use it, required inputs, invocation, success criteria, and troubleshooting boundaries.

**Consequences**: The skill becomes easier to scan and reuse; repository tests need to expand from wording-only assertions to script presence and live execution coverage.

## Implementation Plan (small PRs)

* PR1: add bundled connect script and static contract test updates
* PR2: update `SKILL.md` and README for the new usage flow
* PR3: add live PostgreSQL integration coverage for the shipped script
