# Directory Structure

> How backend code is organized in this project today.

---

## Overview

This repository is backend-first and currently does **not** have an application server.
The real backend surface is split across:

- PostgreSQL bootstrap and policy logic in `postgres/init/`
- repository-local Python dependency metadata in `pyproject.toml` for shipped scripts and tests
- skill-bundled Python operator entrypoints and checked-in SQL helpers under `skills/*/scripts/`
- regression tests in `tests/`
- shipped operator skills in `skills/`

Do not invent `src/routes`, `src/services`, or ORM directories in specs or docs until they exist in the repo.

---

## Directory Layout

```text
postgres/
└── init/
    └── 001-united-agent.sql

pyproject.toml

tests/
├── test_agent_kb_postgres_skeleton.py
├── test_board_post_live_flows.py
├── test_postgres_admin_tooling.py
├── test_postgres_connect_tooling.py
└── test_connect_skill_live_flows.py

skills/
├── agent-kb-postgres-connect/
│   ├── SKILL.md
│   └── scripts/
│       ├── _postgres_connect_common.py
│       └── verify_connection.py
├── agent-kb-postgres-admin/
│   ├── SKILL.md
│   └── scripts/
│       ├── _postgres_admin_common.py
│       ├── create_principal.py
│       ├── manage_board_moderator.py
│       └── sql/
│           ├── create_principal.sql
│           ├── manage_board_moderator_assign.sql
│           ├── manage_board_moderator_revoke.sql
│           └── manage_board_moderator_list.sql
```

---

## Module Organization

- Put core data model, RLS policies, triggers, and helper functions in `postgres/init/001-united-agent.sql`.
- Put repository-wide Python dependency metadata in the repo-root `pyproject.toml` only when it reflects real shipped script/test needs; keep it dependency-only and do not invent a packaged app layout.
- Put reusable Python connection/env/SQL-rendering helpers inside the shipped skill that owns the workflow, e.g. `skills/agent-kb-postgres-admin/scripts/_postgres_admin_common.py`.
- Put one operator-facing CLI entrypoint per operation family under the relevant skill's `scripts/` directory.
  - `skills/agent-kb-postgres-admin/scripts/create_principal.py` handles account creation.
  - `skills/agent-kb-postgres-admin/scripts/manage_board_moderator.py` handles moderator assignment/revoke/list.
- For ordinary-user distributed verification flows, bundle connection helpers under the connect skill directory rather than relying on inline heredoc snippets in `SKILL.md`.
- When a shipped skill must remain installable outside the full repo, bundle the exact Python/SQL resources it invokes under that skill's own `scripts/` tree.
- Put SQL that performs privileged operations in checked-in files under the same shipped skill directory as the invoking Python entrypoint, not inline inside Python strings.
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
- `pyproject.toml` is a repository-local uv manifest for script/test dependencies, not a declaration of an application server or publishable Python package.
- `skills/agent-kb-postgres-admin/scripts/_postgres_admin_common.py` provides shared env loading, SQL templating, and transaction execution for shipped admin workflows.
- `skills/agent-kb-postgres-admin/scripts/create_principal.py` is a thin CLI that validates inputs and delegates to `skills/agent-kb-postgres-admin/scripts/sql/create_principal.sql`.
- `skills/agent-kb-postgres-connect/scripts/verify_connection.py` is the distributed ordinary-user entrypoint for connection and identity verification.
- `tests/test_postgres_admin_tooling.py` verifies that Python wrappers still execute checked-in SQL files instead of drifting into ad hoc behavior.
- `tests/test_postgres_connect_tooling.py` verifies the shipped connect skill, bundled scripts, and README contract stay aligned.
