# Logging Guidelines

> Current logging/output conventions for backend tooling.

---

## Overview

This repository does **not** have a dedicated logging framework yet.

Current behavior is minimal by design:

- Python helper scripts print query results to stdout when the SQL command returns rows.
- Validation failures use `SystemExit` messages.
- SQL failures surface as PostgreSQL exceptions.
- There is no structured JSON logging, request logging, or log aggregation contract yet.

Prefer documenting this minimal reality over inventing `logger.py`, log schemas, or server-style log levels.

---

## Output Levels in Practice

There is no formal log-level API today. Use the following interpretation when touching current scripts:

- **Normal operator output**: rows printed from successful SQL execution.
  - Example: `skills/agent-kb-postgres-admin/scripts/_postgres_admin_common.py` prints returned rows from `cursor.fetchall()`.
- **Validation failure**: `SystemExit` with a concise actionable message.
- **Database failure**: let the raised SQL exception reach the operator.

If you add a real logging library later, update this spec in the same task.

---

## Structured Logging

No structured logging standard exists yet.

Current backend tooling is CLI-oriented, so the shipped contract is:

- readable stdout for successful result rows
- readable exception text for failures

Do not introduce ad hoc JSON logs or custom log wrappers in one script only.

---

## What to Log or Print

Current safe output examples:

- listing board moderators from `skills/agent-kb-postgres-admin/scripts/sql/manage_board_moderator_list.sql`
- returning newly created account rows from `skills/agent-kb-postgres-admin/scripts/sql/create_principal.sql`
- explicit operator guidance such as missing env var names

If you need to add observability before a server exists, prefer small operator-facing context such as:

- action name
- target account or board id
- SQL file path being executed

---

## What NOT to Log

Never print or log:

- database passwords from `AGENT_KB_DB_PASSWORD`
- new account passwords from `--new-password` or `AGENT_KB_NEW_PRINCIPAL_PASSWORD`
- fully rendered SQL when it would expose secrets
- unrelated environment dumps

Avoid noisy duplicate logging. In the current toolchain, surfacing the real exception is usually better than logging and re-raising the same failure.
