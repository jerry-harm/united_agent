# Postgres Admin Skill Wording Update

## Goal

Tighten the `skills/agent-kb-postgres-admin/SKILL.md` wording so it accurately describes where permission enforcement actually lives, including any nearby wording that creates the same kind of overclaim, without changing the operational guidance or helper surface.

## What I already know

* The current skill sometimes implies the Python wrappers themselves enforce the privilege boundary.
* The actual hard permission boundary is in the shipped SQL and database auth helpers.
* `manage_account.py` does an early `require_admin()` precheck in Python, then opens a second connection to execute the SQL helper.
* `manage_account_disable.sql`, `manage_account_delete.sql`, and the `manage_board_moderator_*` SQL files perform their own authorization checks.
* `run_sql_file()` already handles multi-result SQL execution, so the grant/revoke receipt issue is already addressed in code.
* The current review feedback does not require behavior changes, only wording that avoids overclaiming.
* The user wants a broader pass over adjacent wording so similar overclaims are corrected in the same edit, not just one isolated sentence.

## Assumptions (temporary)

* This task is limited to `skills/agent-kb-postgres-admin/SKILL.md`.
* No Python or SQL behavior changes are needed in this task.
* Minimal edits are preferred over restructuring the skill.

## Open Questions

* None for the current scope.

## Requirements (evolving)

* Update the skill so it does not imply that Python wrapper checks are the sole or final permission boundary.
* Update nearby wording that creates the same misunderstanding, even if it is not the exact sentence first called out.
* Clarify that the Python layer mainly provides argument validation, SQL dispatch, and early failure checks, while the effective authorization boundary remains in the shipped SQL / database auth helpers.
* Preserve the current operator guidance and command examples.
* Keep wording consistent with the current implementation.

## Acceptance Criteria (evolving)

* [ ] The skill states that effective authorization is enforced in the shipped SQL / database auth helpers.
* [ ] The skill no longer overstates Python-side enforcement.
* [ ] Nearby wording with the same overclaim is corrected for consistency.
* [ ] No command examples or intended operator workflow change.

## Definition of Done (team quality bar)

* Skill wording updated with minimal, accurate edits.
* Content remains internally consistent.
* No unrelated behavior or docs changes introduced.

## Out of Scope (explicit)

* Refactoring `manage_account.py` to use a single connection.
* Changing SQL helper behavior.
* Adding new tests or new operator commands.

## Technical Notes

* Primary file: `skills/agent-kb-postgres-admin/SKILL.md`
* Relevant implementation references:
  * `skills/agent-kb-postgres-admin/scripts/manage_account.py`
  * `skills/agent-kb-postgres-admin/scripts/_postgres_admin_common.py`
  * `skills/agent-kb-postgres-admin/scripts/sql/manage_account_disable.sql`
  * `skills/agent-kb-postgres-admin/scripts/sql/manage_account_delete.sql`
  * `skills/agent-kb-postgres-admin/scripts/sql/manage_board_moderator_assign.sql`
  * `skills/agent-kb-postgres-admin/scripts/sql/manage_board_moderator_revoke.sql`
  * `skills/agent-kb-postgres-admin/scripts/sql/manage_board_moderator_list.sql`
