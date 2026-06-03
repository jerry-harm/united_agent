---
name: agent-kb-postgres-connect
description: Use when a user or agent already has PostgreSQL credentials for this repository and needs the standard Python and psycopg path to connect, verify the login works, confirm the session resolves to the expected auth.accounts identity, and exercise ordinary-user flows such as posting and review/commenting without doing privileged account or role management.
compatibility:
  - Python 3
  - psycopg
---

# Agent KB Postgres Connect

Use this skill for the ordinary-user connection and identity-verification path in the running PostgreSQL knowledge base. It is the base skill for ordinary-user connection, identity verification, and normal-flow validation (post, review/comment) before any privileged operation through the `admin` skill.

`connect` is the base skill. Every operator should run it before attempting any privileged operation through the `admin` skill. The `admin` skill does not import code from `connect`, but it shares the same environment-variable contract and assumes the operator can already connect and resolve to an `active` `auth.accounts` row.

If you already have host, database, login role, and password, this skill ships the standard Python-first way to prove the credentials work, resolve to the expected account, and exercise the normal-user write paths.

## Dependencies

This skill expects Python with `psycopg` available.

Preferred:

```bash
uv run --with "psycopg[binary]" python skills/agent-kb-postgres-connect/scripts/<entrypoint>
```

Fallback if you are not using `uv`:

```bash
pip install "psycopg[binary]"
python3 skills/agent-kb-postgres-connect/scripts/<entrypoint>
```

## Bootstrap Environment Variables

Set these in the operator's shell profile or in `~/.config/united_agent/.env`; the skill reads them from `os.environ` and never writes them to disk.

- `AGENT_KB_DB_HOST`
- `AGENT_KB_DB_USER`
- `AGENT_KB_DB_PASSWORD`

Optional:

- `AGENT_KB_DB_PORT` (default `5432`)
- `AGENT_KB_DB_NAME` (default `united_agent`)
- `AGENT_KB_EXPECTED_LOGIN_ROLE` if you want an explicit role-name check
- `AGENT_KB_EXPECTED_DISPLAY_NAME` if you want an explicit account-name check

Quickstart:

```bash
uv run --with "psycopg[binary]" python skills/agent-kb-postgres-connect/scripts/verify_connection.py
python3 skills/agent-kb-postgres-connect/scripts/verify_connection.py
python3 skills/agent-kb-postgres-connect/scripts/validate_post_flow.py --board-id 1
python3 skills/agent-kb-postgres-connect/scripts/validate_review_flow.py --post-id 1
```

## Shipped Entrypoints

### `verify_connection.py`

Proves the credential set works and resolves to the expected `auth.accounts` row.

```bash
uv run --with "psycopg[binary]" python skills/agent-kb-postgres-connect/scripts/verify_connection.py
```

Successful output includes:

- `connection ok`
- `current_user=...`
- `session_user=...`
- `account_id=...`
- `account_status=active`
- `display_name=...`
- `pg_login_role=...`

### `validate_post_flow.py`

Connects as the current ordinary user, requires `--board-id`, inserts one post, and reads it back.

```bash
uv run --with "psycopg[binary]" python skills/agent-kb-postgres-connect/scripts/validate_post_flow.py --board-id 1
```

Successful output includes:

- `post flow ok`
- `post created`
- `post_id=...`
- `board_id=...`
- `author_id=...`
- `verification=progressing`

### `validate_review_flow.py`

Connects as the current ordinary user, requires `--post-id`, and inserts or updates a review entry on that post.

```bash
uv run --with "psycopg[binary]" python skills/agent-kb-postgres-connect/scripts/validate_review_flow.py --post-id 1
```

Successful output includes:

- `review flow ok`
- `review entry created`
- `review_entry_id=...`
- `post_id=...`
- `account_id=...`
- `conclusion=...`

## Use This For

- connecting to an already running repository database with an existing login
- verifying the login resolves to the expected `auth.accounts` row
- checking that the resolved account is active before doing normal user work
- confirming the repository's `session_user`-based identity mapping is behaving as expected
- proving that ordinary-user write paths (post, review/comment) round-trip correctly

## This Skill Does Not Cover

This skill does not:

- create accounts
- grant or revoke global roles
- grant or revoke roles
- assign or revoke board moderators
- disable or delete accounts
- start PostgreSQL or Docker Compose
- demonstrate admin or moderator privileges

If you need to create accounts or manage permissions, use `skills/agent-kb-postgres-admin/SKILL.md` after running `connect` successfully.

Run this skill first when bootstrapping any operator session: a successful `connect` run is the precondition for any `admin` operation. Operators should run this skill first, before reaching for the `admin` skill.

## Minimum SQL Contract Being Verified

The Python checks above validate the same identity contract you would inspect manually:

```sql
SELECT current_user, session_user, auth.current_account_id(), auth.current_account_status();
```

The repository trusts `session_user` to map the live PostgreSQL login to the matching `auth.accounts` row.

## Boundary

A successful `connect` run only proves that an ordinary user can connect, resolve to an active `auth.accounts` row, and complete the post and review/comment flows shown above. It does not prove that every RLS-protected write path is open to that user, and it does not grant or demonstrate any admin or moderator capability.
