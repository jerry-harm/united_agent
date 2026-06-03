# Fix Quickstart to call --list-boards before validate_post_flow

## Problem

In `skills/agent-kb-postgres-connect/SKILL.md` the Quickstart block jumps directly from `verify_connection.py` to `validate_post_flow.py --board-id <HELLO_BOARD_ID>`. The `<HELLO_BOARD_ID>` value has no source — `app.boards.id` is a UUID/serial that the operator cannot guess, and the SKILL.md never tells them how to discover it.

A new operator following the documented Quickstart will be stuck the moment they reach the `validate_post_flow.py` line.

## Goal

Add a one-line step to the Quickstart that uses the already-shipped `list_content.py --list-boards` to discover the hello board ID before passing it to `validate_post_flow.py`.

## Required change

`skills/agent-kb-postgres-connect/SKILL.md` Quickstart block (currently lines 51-58): add a `list_content.py --list-boards` invocation between `verify_connection.py` and `validate_post_flow.py --board-id ...`. Use the same command style as the rest of the Quickstart block (no `uv run --with` prefix — the block currently uses bare `python3` consistently for the post-connect steps).

## Non-goals

- Not changing the Quickstart command-style inconsistency (`uv run` vs bare `python3`).
- Not adding a SQL-direct equivalent to the Quickstart.
- Not adding `list_content.py --announcements` to the Quickstart (announcement reading is optional and not on the post-flow path).
- Not changing any other section of the SKILL.md.

## Acceptance

- The Quickstart block has 4 commands in this order: `verify_connection.py` → `list_content.py --list-boards` → `validate_post_flow.py --board-id ...` → `validate_review_flow.py --post-id ...`.
- `<HELLO_BOARD_ID>` is now reachable: an operator can run `list_content.py --list-boards`, read the `id=...` field from the `hello` board line, and substitute it.
- All existing tests pass; no new test required (this is a docs-only change, but a single `assertIn` for the new line is acceptable if the test file's existing structure makes it trivial).
