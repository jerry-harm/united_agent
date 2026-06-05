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
├── test_postgres_admin_tooling.py
├── test_postgres_connect_tooling.py
└── test_connect_skill_live_flows.py

skills/
├── agent-kb-postgres-connect/
│   ├── SKILL.md
│   └── scripts/
│       ├── _postgres_connect_common.py
│       ├── validate_post_flow.py
│       ├── validate_review_flow.py
│       └── verify_connection.py
├── agent-kb-postgres-admin/
│   ├── SKILL.md
│   └── scripts/
│       ├── _postgres_admin_common.py
│       ├── create_principal.py
│       ├── manage_account.py
│       ├── manage_global_role.py
│       └── sql/
│           ├── create_principal.sql
│           ├── manage_account_delete.sql
│           ├── manage_account_disable.sql
│           ├── manage_global_role_grant.sql
│           ├── manage_global_role_list.sql
│           └── manage_global_role_revoke.sql
```

---

## Module Organization

- Split PostgreSQL bootstrap into a small set of ordered top-level files under `postgres/init/`, grouped by responsibility (schema, tables, auth functions, app functions/triggers, permissions/RLS, bootstrap/seed).
- Put repository-wide Python dependency metadata in the repo-root `pyproject.toml` only when it reflects real shipped script/test needs; keep it dependency-only and do not invent a packaged app layout.
- Put reusable Python connection/env/SQL-rendering helpers inside the shipped skill that owns the workflow, e.g. `skills/agent-kb-postgres-admin/scripts/_postgres_admin_common.py`.
- Put one operator-facing CLI entrypoint per operation family under the relevant skill's `scripts/` directory.
  - `skills/agent-kb-postgres-admin/scripts/create_principal.py` handles account creation.
  - `skills/agent-kb-postgres-admin/scripts/manage_account.py` handles account disable/delete lifecycle operations.
  - `skills/agent-kb-postgres-admin/scripts/manage_global_role.py` handles global-role grant/revoke/list.
- For ordinary-user distributed verification flows, bundle connection helpers under the connect skill directory rather than relying on inline heredoc snippets in `SKILL.md`.
  - `skills/agent-kb-postgres-connect/scripts/verify_connection.py` handles connection and identity verification.
  - `skills/agent-kb-postgres-connect/scripts/validate_post_flow.py` handles ordinary-user post validation.
  - `skills/agent-kb-postgres-connect/scripts/validate_review_flow.py` handles ordinary-user review/comment validation.
- When a shipped skill must remain installable outside the full repo, bundle the exact Python/SQL resources it invokes under that skill's own `scripts/` tree.
- Put SQL that performs privileged operations in checked-in files under the same shipped skill directory as the invoking Python entrypoint, not inline inside Python strings.
- Put contract/regression checks in `tests/` and keep them focused on shipped files and behavior.

There are currently **no** HTTP handlers, background workers, or ORM model modules.

---

## Naming Conventions

- SQL bootstrap files: numeric prefix + responsibility slug, e.g. `001-schema.sql`, `006-bootstrap-and-seed.sql`.
- Python scripts: snake_case filenames matching the operation, e.g. `create_principal.py`.
- Shared Python helpers: underscore-prefixed module for internal reuse, e.g. `_postgres_admin_common.py`.
- SQL helper files: snake_case and action-oriented, e.g. `manage_global_role_grant.sql`.
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
- `skills/agent-kb-postgres-admin/scripts/_postgres_admin_common.py` provides shared env loading, SQL templating, and transaction execution for shipped admin workflows.
- `skills/agent-kb-postgres-admin/scripts/create_principal.py` is a thin CLI that validates inputs and delegates to `skills/agent-kb-postgres-admin/scripts/sql/create_principal.sql`.
- `skills/agent-kb-postgres-admin/scripts/manage_account.py` delegates account lifecycle changes to checked-in SQL helpers.
- `skills/agent-kb-postgres-admin/scripts/manage_global_role.py` delegates global-role changes to checked-in SQL helpers.
- `skills/agent-kb-postgres-connect/scripts/verify_connection.py` is the distributed ordinary-user entrypoint for connection and identity verification.
- `skills/agent-kb-postgres-connect/scripts/validate_post_flow.py` and `validate_review_flow.py` keep ordinary-user validation flows split into small task-specific scripts.
- `tests/test_postgres_admin_tooling.py` verifies that Python wrappers still execute checked-in SQL files instead of drifting into ad hoc behavior.
- `tests/test_postgres_connect_tooling.py` verifies the shipped connect skill, bundled scripts, and README contract stay aligned.
