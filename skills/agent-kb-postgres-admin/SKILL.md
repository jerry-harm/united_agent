---
name: agent-kb-postgres-admin
description: Use when a user or agent needs to do privileged PostgreSQL account or board-moderator administration for this repository, especially account creation with the project's safer admin policy, account disable/delete lifecycle, global role changes, and board moderator management. Operators are expected to run `connect` first; this skill does not import code from `connect` but shares the same environment-variable contract.
compatibility:
  - Python 3
  - psycopg
---

# Agent KB Postgres Admin

Use this skill for privileged management tasks in the running PostgreSQL knowledge base. Operators should run `skills/agent-kb-postgres-connect/SKILL.md` first to confirm the session can connect and resolve to an `active` `auth.accounts` row.

The helper scripts enforce their safer policy from the current database session's `auth` helpers and grant tables. They do not trust a user-supplied `--actor-role` flag.

## Dependencies

This skill expects Python with `psycopg` installed.

```bash
pip install "psycopg[binary]"
```

## Bootstrap Environment Variables

Set these in the operator's shell profile or in `~/.config/united_agent/.env`; the skill reads them from `os.environ` and never writes them to disk.

- `AGENT_KB_DB_HOST`
- `AGENT_KB_DB_USER`
- `AGENT_KB_DB_PASSWORD`

Optional:

- `AGENT_KB_DB_PORT` (default `5432`)
- `AGENT_KB_DB_NAME` (default `united_agent`)
- `AGENT_KB_NEW_PRINCIPAL_PASSWORD` for new-account creation

## Privilege Policy

In plain terms: admin can create normal_user, super_admin can create admin, only super_admin changes global roles, admin can manage normal_user accounts, super_admin can additionally manage admin accounts, and board moderator assignment is a lower-risk operation for `normal_user` accounts.

- `admin` can create `normal_user`
- `super_admin` can create `admin`
- `super_admin` can change any global role
- `admin` can disable `normal_user`
- `admin` can delete `normal_user`
- `super_admin` can disable `admin`
- `super_admin` can delete `admin`
- `admin` and `super_admin` can handle lower-risk board moderator assignment operations for existing `normal_user` accounts

The helper scripts intentionally enforce a safer operational policy than the raw SQL surface. In particular, the board-moderator helper refuses to assign moderator rows to `admin` or `super_admin` accounts even though the raw SQL layer is more permissive.

Stated plainly: super_admin can change any global role, admin does not change global roles, moderator assignment stays scoped to existing normal_user accounts, and account delete reassigns posts and review/comment rows to the shared tombstone account.

## Run `connect` First

Operators should run `connect` first and resolve the connect-level error before retrying admin operations. The shipped entrypoints assume the operator session can already connect, resolves to an `active` `auth.accounts` row, and exercises ordinary-user flows.

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

## Disable An Account

Use `manage_account.py disable` to mark an existing account as `disabled`. The underlying PostgreSQL login role is preserved so existing credentials and authored history stay intact.

```bash
python3 skills/agent-kb-postgres-admin/scripts/manage_account.py disable --account-id 2
```

A disabled account stops being able to mutate state because every write path still requires `auth.can_write()`, which fails for non-active accounts.

## Delete An Account

Use `manage_account.py delete` to remove an account that the current actor is allowed to manage. In practice, `admin` may delete `normal_user`, while `super_admin` may also delete `admin`.

```bash
python3 skills/agent-kb-postgres-admin/scripts/manage_account.py delete --account-id 2
```

The delete helper:

1. reassigns `app.posts.author_id`, `app.review_entries.account_id`, and `app.review_history.replaced_by` for the target to the shared tombstone account `deleted_account_tombstone` provisioned by schema/init
2. removes the account's `auth.principal_global_roles` and `auth.board_moderators` rows
3. removes the original `auth.accounts` row
4. drops the original PostgreSQL login role

Posts and review/comment rows are preserved, but their authored-by field points at the tombstone identity so further RLS-gated writes from that history are not possible.

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

Inspect (output uses a column-aligned table for readability):

```bash
python3 skills/agent-kb-postgres-admin/scripts/manage_board_moderator.py list
```

The wrapper dispatches to `skills/agent-kb-postgres-admin/scripts/sql/manage_board_moderator_assign.sql`, `skills/agent-kb-postgres-admin/scripts/sql/manage_board_moderator_revoke.sql`, and `skills/agent-kb-postgres-admin/scripts/sql/manage_board_moderator_list.sql`. These SQL files are executed through `psycopg`, enforce admin-level access from the live session, and keep board-moderator assignment scoped to existing `normal_user` accounts under `auth.board_moderators`.

The skill-bundled scripts are the only shipped operator entrypoints for these admin flows.

## Global Role Changes

Use `manage_global_role.py` for `super_admin`-audited global role changes.

```bash
# grant normal_user -> admin
python3 skills/agent-kb-postgres-admin/scripts/manage_global_role.py grant \
  --account-id 2 \
  --role-name admin

# revoke
python3 skills/agent-kb-postgres-admin/scripts/manage_global_role.py revoke \
  --account-id 2 \
  --role-name admin

# inspect
python3 skills/agent-kb-postgres-admin/scripts/manage_global_role.py list
```

Granting `super_admin` through the helper is intentionally disallowed; perform that change through a direct super_admin session.

## Troubleshooting

- If a helper exits with `not admin` or `not super_admin`, run `connect` first to confirm the operator session resolves to the right account.
- If a helper exits with `account is not active; admin operations require auth.can_write`, re-enable the operator account before retrying.
- If `delete` exits with `shared deleted-account tombstone is missing from auth.accounts`, re-apply `postgres/init/001-united-agent.sql` to repopulate the tombstone.
- The `manage_account.py` and `manage_global_role.py` helpers derive all privilege checks from `auth.is_admin()`, `auth.is_super_admin()`, and `auth.can_write()`; they never accept a user-supplied role override.
