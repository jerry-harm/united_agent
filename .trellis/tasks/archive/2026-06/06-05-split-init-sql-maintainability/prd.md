# split init.sql for maintainability

## Goal

Refactor the PostgreSQL bootstrap layout so the schema/init source stays easy to review and modify as the repository grows, without breaking the current local bootstrap contract.

## What I already know

* The current bootstrap lives in a single file: `postgres/init/001-united-agent.sql`.
* That file now contains schema, tables, helper functions, triggers, grants, RLS, seed data, and upload support in one place.
* The `postgres/init/` directory currently contains only that single SQL file.
* Multiple tests and docs refer directly to `postgres/init/001-united-agent.sql` as the source of truth.
* Current spec text in `.trellis/spec/backend/directory-structure.md` explicitly says to put core data model, RLS policies, triggers, and helper functions in `postgres/init/001-united-agent.sql`.
* The repo currently has no migration framework dependency; `pyproject.toml` only declares `psycopg[binary]`.
* Current backend spec says to keep bootstrap/dev setup in Docker Compose until a migration tool is introduced.
* The user expects future cleanup may reduce or consolidate some test files if the current test surface is too fragmented.
* The user expects some skill-bundled scripts may move into database functions later, so the SQL layout should not assume today's script boundaries are permanent.
* For this task specifically, test-file consolidation is deferred; only the minimum test changes needed for the SQL split should be made.

## Assumptions (temporary)

* The task is about improving maintainability of bootstrap SQL structure, not changing product behavior.
* We should preserve the current local Docker/Postgres init workflow unless this task is explicitly expanded to introduce a migration mechanism.
* Any refactor should minimize churn in operator docs and regression tests.

## Open Questions

* None currently blocking.

## Requirements (evolving)

* Improve maintainability of PostgreSQL bootstrap SQL layout.
* Preserve current bootstrap behavior unless a behavior change is explicitly required.
* Move to multiple top-level init SQL files under `postgres/init/`, executed in filename order by the Postgres container init flow.
* Update tests, docs, and specs so they no longer depend on `postgres/init/001-united-agent.sql` being the single special bootstrap truth file.
* Keep docs/tests/specs aligned with the chosen structure.
* Use a small number of responsibility-based files, roughly six top-level SQL files rather than many narrowly scoped fragments.
* Each SQL file should be independently safe to fail/roll back at its own step boundary rather than depending on one repo-wide `BEGIN; ... COMMIT;` wrapper.
* Do not introduce a migration framework or a custom migration runner in this task.
* Prefer a split that stays compatible with future test consolidation and future movement of some operational logic from skill scripts into database functions.
* Do not consolidate or redesign the test suite in this task beyond the minimal updates required to follow the new bootstrap layout.

## Technical Approach

* Chosen direction: use multiple top-level init files rather than a single aggregator file.
* Rely on the existing Docker/Postgres init behavior that executes `postgres/init/*.sql` in filename order during first-time database initialization.

## Decision (ADR-lite)

**Context**: `postgres/init/001-united-agent.sql` has grown into a large bootstrap file containing schema, tables, functions, grants, RLS, and seed data. The task exists to improve maintainability.

**Decision**: Split bootstrap SQL into multiple top-level files under `postgres/init/` that execute in numeric filename order, instead of keeping a single entry file that includes child files.

**Consequences**: This better matches the current Docker/Postgres initialization model and avoids relying on SQL include behavior, but it requires broader test/doc/spec updates because the repo currently treats `001-united-agent.sql` as a special path. The preferred split is coarse-grained: about six responsibility-based files. Migration design is explicitly deferred; this task should leave the bootstrap structure easier to migrate later without introducing migration machinery now.

## Acceptance Criteria (evolving)

* [ ] The bootstrap SQL structure is split into clearer maintainable units.
* [ ] Local bootstrap still initializes a fresh database correctly.
* [ ] Tests/docs/specs reference the new structure consistently.
* [ ] The refactor does not introduce a migration tool or migration execution layer.
* [ ] Test changes stay narrowly scoped to what the SQL split requires.

## Definition of Done (team quality bar)

* Tests added/updated (unit/integration where appropriate)
* Lint / typecheck / CI green
* Docs/notes updated if behavior changes
* Rollout/rollback considered if risky

## Out of Scope (explicit)

* Changing product permissions or schema semantics unless required by the refactor itself
* Introducing a full migration framework
* Adding a custom manual migration runner or schema version table
* Broad test-suite consolidation or redesign

## Technical Notes

* Inspected `postgres/init/001-united-agent.sql`.
* Inspected `.trellis/spec/backend/directory-structure.md`.
* Searched repo references to `001-united-agent.sql`; many tests/docs/specs currently couple to that exact path.
* Inspected `pyproject.toml`; no migration tool dependency is present today.
* Future evolution to keep in mind: test files may be consolidated later, and some skill-side scripts may later be replaced by database functions.
