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
- Reuse `scripts/_postgres_admin_common.py` for env loading, SQL rendering, and transaction execution instead of re-implementing connection code.
- Use placeholder rendering via `sql.Literal(...).as_string(connection)` rather than manual string concatenation.
- Keep Python entrypoints thin: parse args, validate obvious inputs, delegate to SQL.
- Add or update regression tests whenever changing:
  - bootstrap SQL
  - helper SQL files
  - admin scripts
  - README or shipped skill contracts that tests assert on
- Keep operator-facing schema diagrams in `README.md` aligned with `postgres/init/001-united-agent.sql`, and protect them with explicit README assertions when they are introduced or changed.

---

## Testing Requirements

For current backend changes, run at least:

```bash
python3 -m py_compile scripts/_postgres_admin_common.py scripts/create_principal.py scripts/manage_board_moderator.py
python3 -m unittest discover -s tests -v
```

Expected testing style today:

- static contract checks against SQL, README, and skill files
- no fake framework-specific test scaffolding
- explicit assertions on important strings and file presence

When changing authorization logic, ensure tests still prove:

- `auth.can_write()` gates write-capable flows
- `session_user` remains the identity source
- helper scripts still use checked-in SQL files

---

## Code Review Checklist

- Does the change describe the repo as it actually exists today?
- If SQL behavior changed, is the logic in a checked-in SQL file instead of hidden in Python?
- If authorization changed, does it still derive privilege from DB helper functions?
- If identity changed, does it still resolve from `session_user`?
- Were README / skill docs updated if the operator workflow changed?
- Were matching tests added or updated?
