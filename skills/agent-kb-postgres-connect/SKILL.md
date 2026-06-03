---
name: agent-kb-postgres-connect
description: Use when a user or agent already has PostgreSQL credentials for this repository and needs the standard Python and psycopg path to connect, verify the login works, and confirm the session resolves to the expected auth.accounts identity without doing privileged account creation or role management.
compatibility:
  - Python 3
  - psycopg
---

# Agent KB Postgres Connect

Use this skill for the ordinary-user connection and identity-verification path in the running PostgreSQL knowledge base.

If you already have host, database, login role, and password, this skill ships the standard Python-first way to prove the credentials work and resolve to the expected account.

## Dependencies

This skill expects Python with `psycopg` available.

Preferred:

```bash
uv run --with "psycopg[binary]" python skills/agent-kb-postgres-connect/scripts/verify_connection.py
```

Fallback if you are not using `uv`:

```bash
pip install "psycopg[binary]"
```

## Use This For

- connecting to an already running repository database with an existing login
- verifying the login resolves to the expected `auth.accounts` row
- checking that the resolved account is active before doing normal user work
- confirming the repository's `session_user`-based identity mapping is behaving as expected

## This Skill Does Not Cover

This skill does not:

- create accounts
- grant or revoke roles
- assign board moderators
- start PostgreSQL or Docker Compose

If you need to create accounts or manage permissions, use `skills/agent-kb-postgres-admin/SKILL.md` instead.

## Required Inputs

Obtain these from the server owner or environment config:

- `AGENT_KB_DB_HOST`
- `AGENT_KB_DB_USER`
- `AGENT_KB_DB_PASSWORD`

Optional:

- `AGENT_KB_DB_PORT` (default `5432`)
- `AGENT_KB_DB_NAME` (default `united_agent`)
- `AGENT_KB_EXPECTED_LOGIN_ROLE` if you want an explicit role-name check
- `AGENT_KB_EXPECTED_DISPLAY_NAME` if you want an explicit account-name check

## Verify A Normal Login With The Bundled Script

```bash
uv run --with "psycopg[binary]" python skills/agent-kb-postgres-connect/scripts/verify_connection.py
```

Fallback:

```bash
python3 skills/agent-kb-postgres-connect/scripts/verify_connection.py
```

The only shipped entrypoint lives at `skills/agent-kb-postgres-connect/scripts/verify_connection.py`.

Optional expected-value checks stay environment-driven:

```bash
export AGENT_KB_EXPECTED_LOGIN_ROLE=example_user
export AGENT_KB_EXPECTED_DISPLAY_NAME="Example User"
uv run --with "psycopg[binary]" python skills/agent-kb-postgres-connect/scripts/verify_connection.py
```

Fallback:

```bash
python3 skills/agent-kb-postgres-connect/scripts/verify_connection.py
```

## Minimum SQL Contract Being Verified

The Python check above is validating the same identity contract you would inspect manually:

```sql
SELECT current_user, session_user, auth.current_account_id(), auth.current_account_status();
```

The repository trusts `session_user` to map the live PostgreSQL login to the matching `auth.accounts` row.

## Script Output And Success Criteria

- the connection succeeds with the provided credentials
- `auth.current_account_id()` resolves to a real row in `auth.accounts`
- `auth.current_account_status()` returns `active`
- optional expected-value checks match the provided login role or display name

Successful output includes:

- `connection ok`
- `current_user=...`
- `session_user=...`
- `account_id=...`
- `account_status=active`
- `display_name=...`
- `pg_login_role=...`

## Troubleshooting Boundary

- If connection fails before the query runs, fix host / port / database / login / password first.
- If the query runs but returns no row, the login exists in PostgreSQL but is not mapped the way this repository expects.
- If the account is disabled, stop there; this skill does not override disabled-account policy.
- If you discover the user lacks an account or needs a new role, hand off to `skills/agent-kb-postgres-admin/SKILL.md`.

The bundled script is intentionally narrow: it verifies ordinary-user connectivity and identity mapping only.
