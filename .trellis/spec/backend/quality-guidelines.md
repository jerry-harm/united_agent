# Quality Guidelines

> Code quality standards for the current backend surface.

---

## Overview

The backend is currently a small SQL-first codebase. Quality comes from keeping behavior explicit and checked into the repo:

- database contracts live in SQL files
- Python wrappers stay thin
- README and shipped skills must match reality
- `unittest` files protect current behavior and wording

There is no dedicated lint config or type-checker config in the repo yet. Current lightweight verification is source-compilation for Python plus the existing unittest suite.

---

## Forbidden Patterns

- **Inline privileged SQL inside Python strings** when the repo already uses checked-in SQL files under `scripts/sql/`.
- **User-supplied privilege flags** such as trusting `--actor-role` to decide authorization.
- **Using `current_user` for identity resolution** in auth helpers; current schema requires `session_user`.
- **Role-only write authorization** that forgets `auth.can_write()` for disabled-account protection.
- **Documenting nonexistent backend layers** such as HTTP APIs, ORMs, or services that are not in the repo.
- **Changing operator-facing contract text casually** when tests assert those messages.

---

## Required Patterns

- Keep privileged business rules in SQL and execute them via checked-in files.
- If the repo uses a root `pyproject.toml` for uv, keep it dependency-only for shipped scripts/tests; do not imply this repo is a packaged Python application unless that becomes true.
- Reuse the shipped skill-local common helper (for example `skills/agent-kb-postgres-admin/scripts/_postgres_admin_common.py`) for env loading, SQL rendering, and transaction execution instead of re-implementing connection code.
- Reuse a shared live-test helper module when multiple PostgreSQL integration suites need the same env loading, connection, script-runner, and cleanup behavior.
- If a shipped skill documents executable helper scripts, bundle those helpers under the skill directory and keep docs/tests aligned with that shipped entrypoint.
- Run shipped Python scripts and Python-based verification commands through `uv run ...` from the repo root; do not document bare `python3 ...` invocations as the standard path.
- Use placeholder rendering via `sql.Literal(...).as_string(connection)` rather than manual string concatenation.
- Keep Python entrypoints thin: parse args, validate obvious inputs, delegate to SQL.
- Add or update regression tests whenever changing:
  - bootstrap SQL
  - helper SQL files
  - admin scripts
  - README or shipped skill contracts that tests assert on
- Keep operator-facing schema diagrams in `README.md` aligned with the ordered bootstrap SQL under `postgres/init/`, and protect them with explicit README assertions when they are introduced or changed.

---

## Testing Requirements

For current backend changes, run at least:

```bash
uv run python -m py_compile skills/agent-kb-postgres-admin/scripts/_postgres_admin_common.py skills/agent-kb-postgres-admin/scripts/create_principal.py skills/agent-kb-postgres-admin/scripts/manage_account.py skills/agent-kb-postgres-admin/scripts/manage_global_role.py skills/agent-kb-postgres-admin/scripts/manage_registration_token.py skills/agent-kb-postgres-connect/scripts/_postgres_connect_common.py skills/agent-kb-postgres-connect/scripts/verify_connection.py skills/agent-kb-postgres-connect/scripts/list_content.py skills/agent-kb-postgres-connect/scripts/validate_post_flow.py skills/agent-kb-postgres-connect/scripts/validate_review_flow.py
uv run python -m unittest discover -s tests -v
```

Expected testing style today:

- static contract checks against SQL, README, and skill files
- shipped skill-bundled entrypoints should be checked both statically and, when practical, through live PostgreSQL integration tests
- when live permission coverage expands, split suites by permission theme so failures map cleanly to account creation, admin-only moderation, or content-boundary behavior
- no fake framework-specific test scaffolding
- explicit assertions on important strings and file presence

When changing authorization logic, ensure tests still prove:

- `auth.can_write()` gates write-capable flows
- `session_user` remains the identity source
- helper scripts still use checked-in SQL files
- live authorization tests distinguish between RLS denials that raise an error and denials that surface as zero affected rows
- content-table live coverage checks `read` visibility separately from higher-priority `update/delete` boundaries

---

## Code Review Checklist

- Does the change describe the repo as it actually exists today?
- If SQL behavior changed, is the logic in a checked-in SQL file instead of hidden in Python?
- If authorization changed, does it still derive privilege from DB helper functions?
- If identity changed, does it still resolve from `session_user`?
- Were README / skill docs updated if the operator workflow changed?
- Were matching tests added or updated?
