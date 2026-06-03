---
name: agent-kb-postgres-admin
description: Use when a user or agent needs to do privileged PostgreSQL account or board-moderator administration for this repository, especially account creation with the project's safer admin policy and environment-variable-based connection flow.
compatibility:
  - Python 3
  - psycopg
---

# Agent KB Postgres Admin

Use this skill for privileged management tasks in the running PostgreSQL knowledge base.

The helper scripts enforce their safer policy from the current database session's `auth` helpers and grant tables. They do not trust a user-supplied `--actor-role` flag.

## Dependencies

This skill expects Python with `psycopg` installed.

```bash
pip install "psycopg[binary]"
```

## Use This For

- creating a `normal_user` account
- creating an `admin` account
- assigning or revoking board moderator access for `normal_user` accounts
- checking the current privileged-management policy before touching SQL

## Privilege Policy

In plain terms: admin can create normal_user, super_admin can create admin, only super_admin changes global roles, and board moderator assignment is a lower-risk operation for `normal_user` accounts.

- `admin` can create `normal_user`
- `super_admin` can create `admin`
- `super_admin` can change any global role
- `admin` does not change global roles
- `admin` and `super_admin` can handle lower-risk board moderator assignment operations for existing `normal_user` accounts

The helper scripts intentionally enforce a safer operational policy than the raw SQL surface. In particular, the board-moderator helper refuses to assign moderator rows to `admin` or `super_admin` accounts even though the raw SQL layer is more permissive.

Stated plainly: super_admin can change any global role, admin does not change global roles, and moderator assignment stays scoped to existing normal_user accounts.

## Required Environment Variables

- `AGENT_KB_DB_HOST`
- `AGENT_KB_DB_USER`
- `AGENT_KB_DB_PASSWORD`

Optional:

- `AGENT_KB_DB_PORT` (default `5432`)
- `AGENT_KB_DB_NAME` (default `united_agent`)
- `AGENT_KB_NEW_PRINCIPAL_PASSWORD` for new-account creation

## Create An Account

For an admin creating a normal user:

```bash
python3 skills/agent-kb-postgres-admin/scripts/create_principal.py \
  --principal-type human \
  --display-name "Example User" \
  --global-role normal_user \
  --login-role example_user
```

For a super admin creating an admin:

```bash
python3 skills/agent-kb-postgres-admin/scripts/create_principal.py \
  --principal-type human \
  --display-name "Example Admin" \
  --global-role admin \
  --login-role example_admin
```

Pass the new account password with `--new-password` or `AGENT_KB_NEW_PRINCIPAL_PASSWORD`. The Python entrypoint reads `skills/agent-kb-postgres-admin/scripts/sql/create_principal.sql` and executes it through `psycopg`.

The SQL path targets the dual-schema model:

- `auth.accounts`
- `auth.principal_global_roles`
- `auth.current_account_id()`
- `auth.is_admin()` / `auth.is_super_admin()`

## Manage Board Moderators

Assign a moderator row to an existing `normal_user` account:

```bash
python3 skills/agent-kb-postgres-admin/scripts/manage_board_moderator.py assign \
  --board-id 1 \
  --account-id 2
```

Revoke:

```bash
python3 skills/agent-kb-postgres-admin/scripts/manage_board_moderator.py revoke \
  --board-id 1 \
  --account-id 2
```

Inspect:

```bash
python3 skills/agent-kb-postgres-admin/scripts/manage_board_moderator.py list
```

The wrapper dispatches to `skills/agent-kb-postgres-admin/scripts/sql/manage_board_moderator_assign.sql`, `skills/agent-kb-postgres-admin/scripts/sql/manage_board_moderator_revoke.sql`, and `skills/agent-kb-postgres-admin/scripts/sql/manage_board_moderator_list.sql`. These SQL files are executed through `psycopg`, enforce admin-level access from the live session, and keep board-moderator assignment scoped to existing `normal_user` accounts under `auth.board_moderators`.

The skill-bundled scripts are the only shipped operator entrypoints for these admin flows.

`--principal-id` remains accepted only as a legacy compatibility alias; prefer `--account-id` in all current docs and usage.

## Global Role Changes

Only `super_admin` should change global-role grants directly. There is no helper script for that yet; use a reviewed manual SQL change against `auth.principal_global_roles` only when necessary.

Do not use the board-moderator helper as a substitute for global role changes; it is intentionally narrower than that.
