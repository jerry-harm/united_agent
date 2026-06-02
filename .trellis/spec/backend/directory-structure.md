# Directory Structure

> How backend code is organized in this project today.

---

## Overview

This repository is backend-first and currently does **not** have an application server.
The real backend surface is split across:

- PostgreSQL bootstrap and policy logic in `postgres/init/`
- thin Python admin entrypoints in `scripts/`
- checked-in SQL files executed by those entrypoints in `scripts/sql/`
- regression tests in `tests/`
- shipped operator skills in `skills/`

Do not invent `src/routes`, `src/services`, or ORM directories in specs or docs until they exist in the repo.

---

## Directory Layout

```text
postgres/
└── init/
    └── 001-united-agent.sql

scripts/
├── _postgres_admin_common.py
├── create_principal.py
├── manage_board_moderator.py
└── sql/
    ├── create_principal.sql
    ├── manage_board_moderator_assign.sql
    ├── manage_board_moderator_revoke.sql
    └── manage_board_moderator_list.sql

tests/
├── test_agent_kb_postgres_skeleton.py
└── test_postgres_admin_tooling.py

skills/
├── agent-kb-postgres-admin/SKILL.md
└── agent-kb-postgres-connect/SKILL.md
```

---

## Module Organization

- Put core data model, RLS policies, triggers, and helper functions in `postgres/init/001-united-agent.sql`.
- Put reusable Python connection/env/SQL-rendering helpers in `scripts/_postgres_admin_common.py`.
- Put one operator-facing CLI entrypoint per operation family in `scripts/`.
  - `scripts/create_principal.py` handles account creation.
  - `scripts/manage_board_moderator.py` handles moderator assignment/revoke/list.
- Put SQL that performs privileged operations in checked-in files under `scripts/sql/`, not inline inside Python strings.
- Put contract/regression checks in `tests/` and keep them focused on shipped files and behavior.

There are currently **no** HTTP handlers, background workers, or ORM model modules.

---

## Naming Conventions

- SQL bootstrap files: numeric prefix + project slug, e.g. `001-united-agent.sql`.
- Python scripts: snake_case filenames matching the operation, e.g. `create_principal.py`.
- Shared Python helpers: underscore-prefixed module for internal reuse, e.g. `_postgres_admin_common.py`.
- SQL helper files: snake_case and action-oriented, e.g. `manage_board_moderator_assign.sql`.
- Tests: `test_<area>.py` using `unittest.TestCase` classes.

---

## Examples

- `postgres/init/001-united-agent.sql` centralizes schema, helper functions, triggers, grants, and RLS.
- `scripts/_postgres_admin_common.py` provides shared env loading, SQL templating, and transaction execution.
- `scripts/create_principal.py` is a thin CLI that validates inputs and delegates to `scripts/sql/create_principal.sql`.
- `tests/test_postgres_admin_tooling.py` verifies that Python wrappers still execute checked-in SQL files instead of drifting into ad hoc behavior.
