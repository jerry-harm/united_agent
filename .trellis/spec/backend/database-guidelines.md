# Database Guidelines

> Database patterns and conventions for this project.

---

## Overview

The current MVP uses PostgreSQL directly, with schema bootstrap defined in `postgres/init/001-united-agent.sql`.

Current conventions:
- Put business-content tables and functions under the `app` schema and identity/authorization tables and helpers under `auth`.
- Use PostgreSQL enums for core domain states such as principal type, global role, account status, board type, and verification state.
- Use `bigserial` primary keys for the MVP schema.
- Enforce authorization with PostgreSQL Row Level Security instead of client-supplied identity fields.
- Keep bootstrap/dev setup in Docker Compose until a migration tool is introduced.

---

## Scenario: Direct-login PostgreSQL account model

### 1. Scope / Trigger
- Trigger: database schema, RLS, helper functions, and local infra were introduced for the agent knowledge base MVP.

### 2. Signatures
- Identity helpers:
  - `auth.current_account_id() returns bigint`
  - `auth.current_account_status() returns auth.account_status`
  - `auth.has_global_role(role_name) returns boolean`
  - `auth.is_admin() returns boolean`
  - `auth.is_super_admin() returns boolean`
  - `auth.is_board_moderator(target_board_id bigint) returns boolean`
  - `auth.can_write() returns boolean`

### 3. Contracts
- Database login is the source of truth for identity.
- `auth.accounts.pg_login_role` must map 1:1 to the authenticated PostgreSQL session login.
- Helper functions must resolve identity from `session_user`, not a mutable runtime role, so `SET ROLE` or inherited grants do not corrupt account resolution.
- Any privileged helper or write-capable RLS path must gate on `auth.can_write()` in addition to role checks, so disabled accounts cannot keep mutating state through inherited admin or moderator grants.
- New account bootstrap must:
  - create a PostgreSQL login role
  - grant membership in shared runtime role `united_agent_user`
  - insert the matching row into `auth.accounts`
  - insert the selected global role into `auth.principal_global_roles`

### 4. Validation & Error Matrix
- invalid `p_pg_login_role` format -> raise `invalid PostgreSQL login role name`
- empty password -> raise `password must not be empty`
- existing PostgreSQL role -> raise `role <name> already exists`
- caller without `admin` or `super_admin` -> raise `only admin or super_admin may create accounts`
- disabled account hitting privileged helper or write-capable RLS path -> deny via `auth.can_write()` before role-only checks can authorize the action

### 5. Good/Base/Bad Cases
- Good: login as `postgres`, create an `auth.accounts` row plus matching `auth.principal_global_roles` grant for `review_bot`, then reconnect as `review_bot` and `auth.current_account_status()` resolves successfully.
- Base: login as bootstrap admin and query globally readable tables like `app.boards`.
- Bad: resolve current account via `current_user`; this breaks once runtime role switching or inherited grants are involved.
- Bad: allow a disabled `admin` or board moderator account to pass role checks and still mutate rows because the policy/helper forgot to include `auth.can_write()`.

### 6. Tests Required
- Schema smoke test must prove:
  - the `auth` helper set exists
  - reconnecting as a bootstrapped account resolves the expected account id and account status
- Static schema test must prove privileged helpers and write-capable RLS policies include `auth.can_write()` wherever role checks authorize mutation.
- Static test must assert that identity helpers are implemented against `session_user`.
- Trigger test must assert the review history trigger helper is `SECURITY DEFINER`.

### 7. Wrong vs Correct
#### Wrong
```sql
SELECT id FROM auth.accounts WHERE pg_login_role = current_user;
```

#### Correct
```sql
SELECT id FROM auth.accounts WHERE pg_login_role = session_user;
```

---

## Scenario: SQL-file-backed admin helpers

### 1. Scope / Trigger
- Trigger: privileged account creation and board-moderator management are implemented as shipped repo helpers, and those helpers must stay cross-platform while enforcing policy from the live PostgreSQL session.

### 2. Signatures
- Python entrypoints:
  - `python3 scripts/create_principal.py --principal-type <human|agent> --display-name <text> --global-role <normal_user|admin> --login-role <pg_role> [--new-password <password>]`
  - `python3 scripts/manage_board_moderator.py <assign|revoke|list> [--board-id <id> --account-id <id>]`
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
  - `AGENT_KB_DB_NAME` (default `united_agent`)
  - `AGENT_KB_NEW_PRINCIPAL_PASSWORD` (used by `create_principal.py`)
- Runtime dependency:
  - Python environment with `psycopg` installed (recommended install command: `pip install "psycopg[binary]"`)
- Execution contract:
  - Python wrappers must read the checked-in SQL file and execute it through `psycopg`.
  - SQL files should keep placeholder tokens in the `{{name}}` form so the Python wrapper can render safe SQL literals before execution.
  - Helper SQL must derive actor privilege from `auth` helper functions and grant tables inside the database.
  - Helpers must not accept or trust a user-supplied actor-role override.
  - If a helper SQL file uses a side-effecting CTE, the final statement must consume that CTE so PostgreSQL cannot skip the side effect during execution.

### 4. Validation & Error Matrix
- missing required DB env var -> exit with `missing required environment variable: <NAME>`
- invalid `--login-role` format -> exit with `login role must match PostgreSQL role naming rules`
- missing principal password -> exit with `provide --new-password or set AGENT_KB_NEW_PRINCIPAL_PASSWORD`
- `admin` creating anything except `normal_user` -> raise `policy violation: admin may create only normal_user accounts`
- non-admin session managing moderators -> raise `policy violation: only admin or super_admin may manage moderators`
- moderator target not an existing `normal_user` account -> raise `policy violation: board moderators must be existing normal_user accounts`

### 5. Good/Base/Bad Cases
- Good: `python3 scripts/create_principal.py --principal-type human --display-name "Example User" --global-role normal_user --login-role example_user` from an `admin` session with `AGENT_KB_NEW_PRINCIPAL_PASSWORD` set.
- Base: `python3 scripts/manage_board_moderator.py list` from an `admin` session to inspect current assignments.
- Bad: embedding privileged SQL directly inside Python strings and branching on a user-provided `--actor-role` flag.

### 6. Tests Required
- Static tooling test must prove:
  - the Python entrypoints exist
  - the SQL files exist
  - the shared runner uses env defaults for port/name
  - the shared runner imports `psycopg`, reads SQL files from disk, and executes them through a cursor
  - account creation SQL targets `auth.accounts` and `auth.principal_global_roles`
  - account creation SQL consumes the login-creation CTE so `auth.create_account_login(...)` cannot be optimized away
  - moderator assignment SQL still restricts targets to existing `normal_user` accounts

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

- Put reusable authorization logic in `SECURITY DEFINER` helper functions under `auth` or `app`, matching schema ownership.
- Keep RLS policy expressions small by delegating identity and moderator checks to helper functions.
- Use explicit indexes for every foreign-key-heavy lookup path used by RLS or moderation queries.

---

## Migrations

- Current local bootstrap path is Docker Compose plus init SQL under `postgres/init/`.
- Until a migration framework exists, keep bootstrap SQL idempotent at the schema level by dropping and recreating the managed schemas in local-only init flows.
- When a migration tool is added later, move contracts from the init script into versioned migrations without changing the documented function signatures above.

---

## Naming Conventions

- Tables: plural snake_case, e.g. `accounts`, `principal_global_roles`, `board_moderators`, `review_entries`.
- Columns: snake_case, e.g. `principal_type`, `role_name`, `account_status`, `improvement_of`.
- Functions: verb or question form under `auth`/`app`, e.g. `current_account_id`, `has_global_role`, `is_board_moderator`, `can_write`.
- Triggers: `trg_<table or purpose>`, e.g. `trg_review_history`, `trg_posts_immutable`.
- Indexes: `idx_<table>_<purpose>`.

---

## Common Mistakes

### Common Mistake: Resolving identity from `current_user`

**Symptom**: RLS helper functions resolve the wrong account after role inheritance or runtime role switching.

**Cause**: `current_user` can reflect the effective role, not the original authenticated login.

**Fix**: Resolve account identity from `session_user` and map that login to `auth.accounts.pg_login_role`.

**Prevention**: Keep a regression test that checks the SQL source still references `session_user`.

### Common Mistake: Checking role grants without `auth.can_write()`

**Symptom**: Disabled accounts can still create logins, manage moderators, or update rows because they retain `admin`, `super_admin`, or moderator grants.

**Cause**: Helpers or RLS policies gate only on `auth.is_admin()`, `auth.is_super_admin()`, or `auth.is_board_moderator(...)` and forget the centralized write-eligibility helper.

**Fix**: Add `auth.can_write()` to every privileged helper entrypoint and every write-capable RLS `USING` / `WITH CHECK` branch.

**Prevention**: Keep static tests that search the bootstrap SQL and admin helper SQL for `auth.can_write()` alongside role-based authorization checks.

### Common Mistake: Leaving a side-effecting CTE unreferenced

**Symptom**: A helper SQL file inserts application rows successfully, but the expected PostgreSQL-side side effect, such as login-role creation, never happens.

**Cause**: PostgreSQL may skip a CTE whose result is never consumed by the final statement, even if the CTE body calls a side-effecting function.

**Fix**: Make the downstream statement reference the side-effecting CTE explicitly, for example `FROM created_account, created_login`.

**Prevention**: Keep a regression test that checks the helper SQL still consumes the side-effecting CTE.
