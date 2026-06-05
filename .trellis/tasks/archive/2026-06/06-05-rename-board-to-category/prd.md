# rename board to category

## Goal

Rename the current top-level content container concept from "board" to "category" in the repository, with the exact scope to be decided before implementation.

## What I already know

* `board` is currently used in many layers, not just user-facing copy.
* Database/schema usage includes objects such as `app.boards`, `auth.board_moderators`, `app.board_type`, `board_id`, `auth.is_board_moderator(...)`, and `auth.can_moderate_board(...)`.
* Skill/admin tooling usage includes files and commands such as `manage_board_moderator.py`, `manage_board_moderator_*.sql`, and CLI flags like `--board-id`.
* Tests, docs, and README contain many user-facing references like `hello board`, `announcement board`, and helper APIs like `create_board(...)`.
* The current content model and permission model are built around board-scoped moderation.

## Assumptions (temporary)

* The desired new term is exactly `category` in English.
* The rename will be a full internal and external clean-break refactor, not a user-facing wording change only.
* Moderator-role concepts and moderator-only flows should be removed rather than preserved under new names.

## Open Questions

* None currently blocking.

## Requirements (evolving)

* Rename the concept from `board` to `category` in the chosen scope.
* Apply the rename across internal implementation as well as user-facing/docs/CLI wording.
* Do a clean break to `category` without preserving backward compatibility for old `board` names.
* Remove the moderator role/model instead of renaming it.
* Remove moderator-only capabilities rather than reassigning them to another lower-privilege role.

## Technical Approach

* Chosen direction: full rename rather than user-facing wording only.
* Chosen direction: remove moderator-role concepts rather than renaming them to category-moderator.
* Chosen direction: delete moderator-only scoped capabilities entirely; keep only the remaining non-moderator role model.

## Decision (ADR-lite)

**Context**: `board` is currently embedded in database schema, helper functions, script names, CLI flags, tests, and docs. A partial wording-only rename would leave the repo with mixed terminology. The current system also has a board-scoped moderator model that the user now wants removed instead of renamed.

**Decision**: Do a full rename to `category` across the repository, do it as a clean break without compatibility aliases for old `board` names, and remove moderator-role concepts rather than carrying them forward under the new name.

**Consequences**: This yields cleaner terminology consistency, but it is a larger and riskier refactor that touches schema contracts, scripts, tests, docs, and live workflow examples. Existing callers must move to the new names immediately because no compatibility layer will remain. The permission model will also simplify because moderator-only concepts and scoped moderation flows will be removed instead of renamed or reassigned.

## Acceptance Criteria (evolving)

* [ ] All in-scope references use `category` consistently.
* [ ] Remaining preserved `board` references, if any, are only intentional historical/test-fixture text that cannot be renamed without changing the meaning of the assertion.
* [ ] Moderator-role concepts and moderator-only capabilities are removed from the repository surface.

## Definition of Done (team quality bar)

* Tests added/updated (unit/integration where appropriate)
* Lint / typecheck / CI green
* Docs/notes updated if behavior changes
* Rollout/rollback considered if risky

## Out of Scope (explicit)

* Backward-compatibility aliases for old `board` names
* Introducing a replacement lower-privilege moderation role

## Technical Notes

* Inspected repo-wide references for `board`, `boards`, `Board`, and `board_`.
* Likely affected areas include `postgres/init/*.sql`, `tests/`, `README.md`, `docs/developer-guide.md`, and `skills/agent-kb-postgres-admin/`.
