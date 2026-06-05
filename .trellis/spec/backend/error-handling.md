# Error Handling

> How backend errors are handled in the current SQL-first toolchain.

---

## Overview

This repo does not have a backend error framework yet. Current error handling is intentionally simple:

- Python CLI validation failures exit with `SystemExit` and a specific operator-facing message.
- PostgreSQL policy/validation failures raise SQL exceptions with specific messages.
- The shared Python runner does not swallow database exceptions.
- Tests assert on important error text, so messages are part of the current contract.

There is no HTTP/API error envelope because there is no API server in this repo yet.

---

## Error Types

### Python entrypoint validation

Use `raise SystemExit("...")` for invalid CLI or environment input.

Real examples:

- `skills/agent-kb-postgres-admin/scripts/_postgres_admin_common.py` raises `SystemExit` when required DB env vars are missing.
- `skills/agent-kb-postgres-admin/scripts/create_principal.py` raises `SystemExit("login role must match PostgreSQL role naming rules")` for invalid login names.
- `skills/agent-kb-postgres-admin/scripts/create_principal.py` raises `SystemExit("provide --new-password or set AGENT_KB_NEW_PRINCIPAL_PASSWORD")` when no password is provided.

### SQL policy and integrity failures

Use `RAISE EXCEPTION` inside SQL helpers/functions for permission and domain violations.

Real examples:

- `postgres/init/003-auth-functions.sql` raises `only admin or super_admin may create accounts` in `auth.create_account_login(...)`.
- `skills/agent-kb-postgres-admin/scripts/sql/create_principal.sql` raises `policy violation: admin may create only normal_user accounts`.

---

## Error Handling Patterns

- Validate cheap input at the Python CLI boundary before opening the main SQL flow.
- Keep authorization and domain enforcement in the database, not in user-supplied flags.
- Let `psycopg` exceptions propagate; do not wrap them in generic catch-all error text.
- Use transaction boundaries when running checked-in SQL files:
  - `skills/agent-kb-postgres-admin/scripts/_postgres_admin_common.py` sets `connection.autocommit = False`
  - commits only after successful execution
- When a SQL function performs side effects before a later failure, clean up and re-raise.
  - `auth.create_account_login(...)` drops the created PostgreSQL role in its `EXCEPTION` block before `RAISE`.

---

## API Error Responses

Not applicable yet. This repository does not currently implement an API server.

When an API is introduced later, add a dedicated error-response contract here instead of extrapolating from the current CLI/database patterns.

---

## Common Mistakes

### Hiding the real database error

Bad:

- catching every exception in Python and returning a generic success/failure string

Current preferred behavior:

- validate obvious operator input early
- otherwise let the concrete SQL error surface to the operator/test

### Enforcing policy only in Python

Bad:

- trusting a CLI flag such as `--actor-role`

Correct:

- derive actor privilege from `auth.is_admin()`, `auth.is_super_admin()`, and `auth.can_write()` in SQL

### Changing error text without updating tests

Several tests assert on exact messages in SQL files, helper scripts, and README/skills. If the wording changes intentionally, update the relevant tests in `tests/` in the same task.
