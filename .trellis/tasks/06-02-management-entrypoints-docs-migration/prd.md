# management entrypoints and docs migration

## Goal

Adapt operational helper entrypoints, tests, and project documentation to the new dual-schema authorization model after the core schema refactor lands.

## Scope

* Migrate admin/helper entrypoints to the `auth.accounts` + grant-table layout.
* Update SQL helper files and Python wrappers that currently assume `principals` or direct role columns.
* Refresh README/spec/docs wording to match the new `auth` / `app` split and account/grant terminology.
* Update verification coverage for the management flows and operational helper contracts that consume the new schema model.

## Non-Goals

* No new business model changes.
* No data migration workflow for existing bootstrap data.
* No extra role expansion beyond the agreed MVP role set.
* No separate DDL-capability helper model.

## Requirements

* Keep terminology aligned with the new design:
  * `auth.accounts`
  * `auth.principal_global_roles`
  * `auth.board_moderators`
* Ensure helper tooling no longer depends on `business_role` as a single source-of-truth column.
* Keep destructive dev bootstrap reset acceptable; do not add migration compatibility machinery.
* Preserve current policy intent: DDL privileges remain operational, while business authorization stays in helper/grant logic.

## Expected Files/Areas

* `scripts/create_principal.py`
* `scripts/manage_board_moderator.py`
* `scripts/sql/*.sql`
* `README.md`
* `.trellis/spec/**/*`
* tests covering admin/helper flows and documentation-backed operational contracts

## Acceptance Criteria

* [ ] Management entrypoints work against the new dual-schema model.
* [ ] SQL helper files and wrappers use account/grant-based assumptions.
* [ ] Project docs/spec wording no longer describes the old principals + direct-role-column model as current.
* [ ] Verification coverage is refreshed for the updated operational flows.

## Notes

This task assumes the core schema and RLS work from `.trellis/tasks/06-02-dual-schema-permission-model-refactor/` has already landed. Schema/bootstrap/RLS helper correctness stays owned by that first task; this follow-up covers operational entrypoints, docs/spec wording, and verification that those entrypoints now target the new account/grant model.
