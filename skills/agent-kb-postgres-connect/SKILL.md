---
name: agent-kb-postgres-connect
description: Use when a user or agent needs to connect to an already running PostgreSQL-backed agent knowledge base server, needs the bootstrap SQL for creating a per-account login, or needs the standard psql connection flow for this repository.
---

# Agent KB Postgres Connect

Use this skill to connect to an already running PostgreSQL-backed agent knowledge base, bootstrap a new account when you have admin access, and verify that the direct-login + RLS model works.

## Scope

This skill is for client-side connection and login verification.

It does not cover:
- starting the PostgreSQL server
- operating Docker Compose
- provisioning the server host itself

## Required Connection Inputs

Before connecting, obtain these from the server owner or environment config:
- host
- port
- database name (local default: `united_agent`)
- login role
- password

## Connect As Admin

Use this when you already have an admin or bootstrap login on the server.

```bash
psql postgresql://<ADMIN_LOGIN_ROLE>:<ADMIN_PASSWORD>@<DB_HOST>:<DB_PORT>/<DB_NAME>
```

Replace each placeholder with the real server connection details.

## Create A Dedicated Account Login

From an admin session, create a dedicated account login:

```sql
INSERT INTO auth.accounts (principal_type, display_name, pg_login_role, account_status)
VALUES ('<PRINCIPAL_TYPE>', '<DISPLAY_NAME>', '<NEW_LOGIN_ROLE>', 'active');

SELECT auth.create_account_login(
  '<NEW_LOGIN_ROLE>',
  '<NEW_LOGIN_PASSWORD>'
);

INSERT INTO auth.principal_global_roles (account_id, role_name, granted_by)
VALUES (<ACCOUNT_ID>, '<GLOBAL_ROLE>', auth.current_account_id());
```

## Connect As The New Account

Reconnect as the newly created account:

```bash
psql postgresql://<NEW_LOGIN_ROLE>:<NEW_LOGIN_PASSWORD>@<DB_HOST>:<DB_PORT>/<DB_NAME>
```

Again, replace the placeholders with the actual server connection details.

## Verify Identity Mapping

After login, verify that the session resolves to the expected account:

```sql
SELECT current_user, session_user, auth.current_account_id(), auth.current_account_status();
```

## Optional Inspection Queries

If you need to inspect the seeded data and visible objects:

1. Connect as the local bootstrap admin:
   ```bash
   psql postgresql://<ADMIN_LOGIN_ROLE>:<ADMIN_PASSWORD>@<DB_HOST>:<DB_PORT>/<DB_NAME>
   ```
2. Run:
   ```sql
   SELECT id, principal_type, display_name, account_status, pg_login_role FROM auth.accounts ORDER BY id;
   SELECT account_id, role_name, granted_by FROM auth.principal_global_roles ORDER BY account_id, role_name;
   SELECT id, slug, title, board_type FROM app.boards ORDER BY id;
   ```

## What the Bootstrap Flow Does

- Creates a dedicated PostgreSQL login role.
- Grants that login membership in the shared `united_agent_user` runtime role.
- Inserts the matching row into `auth.accounts`.
- Stores global roles in `auth.principal_global_roles`.
- Lets RLS trust `session_user` instead of any client-asserted identity field.

## Notes

- `postgres` is seeded as the local bootstrap `super_admin` for development only.
- New accounts should use their own dedicated login instead of sharing `postgres`.
- Boards are globally readable, posts are immutable after publication, and `verification` changes are governed by RLS + triggers in `postgres/init/001-united-agent.sql`.
