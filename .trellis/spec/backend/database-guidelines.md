# Database Guidelines

> Database patterns and conventions for this project.

---

## Overview

The current MVP uses PostgreSQL directly, with schema bootstrap defined in `postgres/init/001-agent-knowledge-base.sql`.

Current conventions:
- Put application tables and functions under the `app` schema.
- Use PostgreSQL enums for core domain states such as principal type, business role, board type, and verification state.
- Use `bigserial` primary keys for the MVP schema.
- Enforce authorization with PostgreSQL Row Level Security instead of client-supplied identity fields.
- Keep bootstrap/dev setup in Docker Compose until a migration tool is introduced.

---

## Scenario: Direct-login PostgreSQL principal model

### 1. Scope / Trigger
- Trigger: database schema, RLS, helper functions, and local infra were introduced for the agent knowledge base MVP.

### 2. Signatures
- Bootstrap function:
  - `app.bootstrap_principal(p_principal_type app.principal_type, p_display_name text, p_business_role app.business_role, p_pg_login_role text, p_pg_password text) returns app.principals`
- Identity helpers:
  - `app.current_principal_id() returns bigint`
  - `app.current_business_role() returns app.business_role`
  - `app.is_board_moderator(target_board_id bigint) returns boolean`

### 3. Contracts
- Database login is the source of truth for identity.
- `app.principals.pg_login_role` must map 1:1 to the authenticated PostgreSQL session login.
- Helper functions must resolve identity from `session_user`, not a mutable runtime role, so `SET ROLE` or inherited grants do not corrupt principal resolution.
- New principal bootstrap must:
  - create a PostgreSQL login role
  - grant membership in shared runtime role `agent_kb_user`
  - insert the matching row into `app.principals`

### 4. Validation & Error Matrix
- invalid `p_pg_login_role` format -> raise `invalid PostgreSQL login role name`
- empty password -> raise `password must not be empty`
- existing PostgreSQL role -> raise `role <name> already exists`
- caller without `admin` or `super_admin` -> raise `only admins may bootstrap principals`

### 5. Good/Base/Bad Cases
- Good: login as `postgres`, call `bootstrap_principal('agent', 'Review Bot', 'normal_user', 'review_bot', 'secret')`, then reconnect as `review_bot` and `app.current_business_role()` resolves to `normal_user`.
- Base: login as bootstrap admin and query globally readable tables like `app.boards`.
- Bad: resolve current principal via `current_user`; this breaks once runtime role switching or inherited grants are involved.

### 6. Tests Required
- Schema smoke test must prove:
  - bootstrap function exists
  - RLS helpers exist
  - reconnecting as a bootstrapped principal resolves the expected principal id and business role
- Static test must assert that identity helpers are implemented against `session_user`.
- Trigger test must assert the review history trigger helper is `SECURITY DEFINER`.

### 7. Wrong vs Correct
#### Wrong
```sql
SELECT id FROM app.principals WHERE pg_login_role = current_user;
```

#### Correct
```sql
SELECT id FROM app.principals WHERE pg_login_role = session_user;
```

---

## Scenario: SQL-file-backed admin helpers

### 1. Scope / Trigger
- Trigger: privileged principal creation and board-moderator management are implemented as shipped repo helpers, and those helpers must stay cross-platform while enforcing policy from the live PostgreSQL session.

### 2. Signatures
- Python entrypoints:
  - `python3 scripts/create_principal.py --principal-type <human|agent> --display-name <text> --business-role <normal_user|admin> --login-role <pg_role> [--new-password <password>]`
  - `python3 scripts/manage_board_moderator.py <assign|revoke|list> [--board-id <id> --principal-id <id>]`
- SQL files executed by those entrypoints:
  - `scripts/sql/create_principal.sql`
  - `scripts/sql/manage_board_moderator_assign.sql`
  - `scripts/sql/manage_board_moderator_revoke.sql`
  - `scripts/sql/manage_board_moderator_list.sql`

### 3. Contracts
- Required environment keys:
  - `AGENT_KB_DB_HOST`
  - `AGENT_KB_DB_USER`
  - `AGENT_KB_DB_PASSWORD`
- Optional environment keys:
  - `AGENT_KB_DB_PORT` (default `5432`)
  - `AGENT_KB_DB_NAME` (default `agent_knowledge_base`)
  - `AGENT_KB_NEW_PRINCIPAL_PASSWORD` (used by `create_principal.py`)
- Runtime dependency:
  - Python environment with `psycopg` installed (recommended install command: `pip install "psycopg[binary]"`)
- Execution contract:
  - Python wrappers must read the checked-in SQL file and execute it through `psycopg`.
  - SQL files should keep placeholder tokens in the `{{name}}` form so the Python wrapper can render safe SQL literals before execution.
  - Helper SQL must derive actor privilege from `app.current_business_role()` inside the database.
  - Helpers must not accept or trust a user-supplied actor-role override.

### 4. Validation & Error Matrix
- missing required DB env var -> exit with `missing required environment variable: <NAME>`
- invalid `--login-role` format -> exit with `login role must match PostgreSQL role naming rules`
- missing principal password -> exit with `provide --new-password or set AGENT_KB_NEW_PRINCIPAL_PASSWORD`
- `admin` creating anything except `normal_user` -> raise `policy violation: admin may create only normal_user principals`
- non-admin session managing moderators -> raise `policy violation: only admin or super_admin may manage moderators`
- moderator target not an existing `normal_user` principal -> raise `policy violation: board moderators must be existing normal_user principals`

### 5. Good/Base/Bad Cases
- Good: `python3 scripts/create_principal.py --principal-type human --display-name "Example User" --business-role normal_user --login-role example_user` from an `admin` session with `AGENT_KB_NEW_PRINCIPAL_PASSWORD` set.
- Base: `python3 scripts/manage_board_moderator.py list` from an `admin` session to inspect current assignments.
- Bad: embedding privileged SQL directly inside Python strings and branching on a user-provided `--actor-role` flag.

### 6. Tests Required
- Static tooling test must prove:
  - the Python entrypoints exist
  - the SQL files exist
  - the shared runner uses env defaults for port/name
  - the shared runner imports `psycopg`, reads SQL files from disk, and executes them through a cursor
  - principal creation SQL still calls `app.bootstrap_principal(...)`
  - moderator assignment SQL still restricts targets to existing `normal_user` principals

### 7. Wrong vs Correct
#### Wrong
```python
cursor.execute(inline_sql_with_actor_role_flag)
```

#### Correct
```python
with psycopg.connect(...) as connection:
    rendered_sql = render_sql(connection, sql_path.read_text(encoding="utf-8"), variables)
    with connection.cursor() as cursor:
        cursor.execute(rendered_sql)
```

---

## Query Patterns

- Put reusable authorization logic in `SECURITY DEFINER` helper functions under `app`.
- Keep RLS policy expressions small by delegating identity and moderator checks to helper functions.
- Use explicit indexes for every foreign-key-heavy lookup path used by RLS or moderation queries.

---

## Migrations

- Current local bootstrap path is Docker Compose plus init SQL under `postgres/init/`.
- Until a migration framework exists, keep bootstrap SQL idempotent at the schema level by dropping and recreating the `app` schema in local-only init flows.
- When a migration tool is added later, move contracts from the init script into versioned migrations without changing the documented function signatures above.

---

## Naming Conventions

- Tables: plural snake_case, e.g. `principals`, `board_moderators`, `review_entries`.
- Columns: snake_case, e.g. `principal_type`, `business_role`, `improvement_of`.
- Functions: verb or question form under `app`, e.g. `bootstrap_principal`, `current_business_role`, `is_board_moderator`.
- Triggers: `trg_<table or purpose>`, e.g. `trg_review_history`, `trg_posts_immutable`.
- Indexes: `idx_<table>_<purpose>`.

---

## Common Mistakes

### Common Mistake: Resolving identity from `current_user`

**Symptom**: RLS helper functions resolve the wrong principal after role inheritance or runtime role switching.

**Cause**: `current_user` can reflect the effective role, not the original authenticated login.

**Fix**: Resolve principal identity from `session_user` and map that login to `app.principals.pg_login_role`.

**Prevention**: Keep a regression test that checks the SQL source still references `session_user`.
