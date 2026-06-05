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
    ├── 001-schema.sql
    ├── 002-tables.sql
    ├── 003-auth-functions.sql
    ├── 004-app-functions-and-triggers.sql
    ├── 005-permissions-and-rls.sql
    └── 006-bootstrap-and-seed.sql

pyproject.toml

tests/
├── test_agent_kb_postgres_skeleton.py
├── test_category_post_live_flows.py
├── test_create_principal_live_flows.py
├── test_postgres_user_tooling.py
├── test_registration_token_live_flows.py
└── test_user_skill_live_flows.py

skills/
├── agent-kb-postgres-user/
│   ├── SKILL.md
│   └── scripts/
│       ├── _agent_kb_user_common.py
│       ├── call_helper.py
│       └── run_sql.py
```

---

## Module Organization

- Split PostgreSQL bootstrap into a small set of ordered top-level files under `postgres/init/`, grouped by responsibility (schema, tables, auth functions, app functions/triggers, permissions/RLS, bootstrap/seed).
- Put repository-wide Python dependency metadata in the repo-root `pyproject.toml` only when it reflects real shipped script/test needs; keep it dependency-only and do not invent a packaged app layout.
- Put reusable Python connection/env/SQL-rendering helpers inside the shipped skill that owns the workflow, e.g. `skills/agent-kb-postgres-user/scripts/_agent_kb_user_common.py`.
- Keep the public operator surface collapsed to two generic CLI entrypoints under the shipped skill's `scripts/` directory.
  - `skills/agent-kb-postgres-user/scripts/call_helper.py` handles direct helper/function execution by `schema.function` name.
  - `skills/agent-kb-postgres-user/scripts/run_sql.py` handles ad hoc SQL strings and checked-in `.sql` files.
- When a shipped skill must remain installable outside the full repo, bundle the exact Python/SQL resources it invokes under that skill's own `scripts/` tree.
- Put SQL that performs privileged operations or reusable reads in checked-in files or stable PostgreSQL functions, not inline inside Python strings.
- Put contract/regression checks in `tests/` and keep them focused on shipped files and behavior.

There are currently **no** HTTP handlers, background workers, or ORM model modules.

---

## Naming Conventions

- SQL bootstrap files: numeric prefix + responsibility slug, e.g. `001-schema.sql`, `006-bootstrap-and-seed.sql`.
- Python scripts: snake_case filenames matching the public role, e.g. `call_helper.py`, `run_sql.py`.
- Shared Python helpers: underscore-prefixed module for internal reuse, e.g. `_agent_kb_user_common.py`.
- SQL helper files: snake_case and action-oriented when checked in for reuse, e.g. `list_content_announcements.sql`.
- Tests: `test_<area>.py` using `unittest.TestCase` classes.

---

## Examples

- `postgres/init/001-schema.sql` resets managed schemas, locks down `public`, creates the shared runtime role, and defines enums.
- `postgres/init/002-tables.sql` defines tables, the upload MIME helper needed by table constraints, and indexes.
- `postgres/init/003-auth-functions.sql` defines auth/account-management helpers.
- `postgres/init/004-app-functions-and-triggers.sql` defines app-layer triggers, file URL helpers, and ranking views.
- `postgres/init/005-permissions-and-rls.sql` defines grants, column privileges, RLS enablement, and policies.
- `postgres/init/006-bootstrap-and-seed.sql` provisions bootstrap identities, default categories, and the startup announcement.
- `pyproject.toml` is a repository-local uv manifest for script/test dependencies, not a declaration of an application server or publishable Python package.
- `skills/agent-kb-postgres-user/scripts/_agent_kb_user_common.py` provides shared env loading, helper-signature lookup, SQL templating, and transaction execution for the single shipped user skill.
- `skills/agent-kb-postgres-user/scripts/call_helper.py` is a thin CLI that validates inputs and dispatches directly to a stable PostgreSQL helper/function by `schema.function` name.
- `skills/agent-kb-postgres-user/scripts/run_sql.py` is the generic query runner for inline SQL and checked-in SQL files.
- `tests/test_postgres_user_tooling.py` verifies that the one-skill/two-script contract and repo docs stay aligned.
- `tests/test_user_skill_live_flows.py` verifies the shipped user skill's helper and SQL flows against a live PostgreSQL instance.
