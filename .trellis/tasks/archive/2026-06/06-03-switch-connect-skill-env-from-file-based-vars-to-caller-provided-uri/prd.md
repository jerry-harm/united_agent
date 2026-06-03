# Switch Connect Skill Env from File-based Vars to Caller-Provided URI

## Problem

The current connect skill specifies 5 separate environment variables (`AGENT_KB_DB_HOST`, `AGENT_KB_DB_PORT`, etc.) that the operator is supposed to set in their shell profile or `~/.config/united_agent/.env`. This framing implies:

1. The credentials should be stored in a file on disk — a security risk and wrong mental model
2. Five separate vars is more cumbersome than a single URI string
3. The SKILL.md says "reads them from `os.environ` and never writes them to disk" but the surrounding text still frames it as "set these in your shell profile" — still file-based

The correct mental model is: **the agent/client that invokes the skill already has the connection info; the skill just receives it at runtime**. No file storage involved.

## Goal

Replace the 5-separate-env-var pattern with a single `DATABASE_URL` URI (`postgres://username:password@host:port/dbname`), and reframe the SKILL.md language to make clear the env is provided by the calling client, not stored in a file.

## Required Changes

### 1. `_postgres_connect_common.py`

Change the connection logic to:
- Accept `DATABASE_URL` env var as the primary source
- If `DATABASE_URL` is set, parse it with `psycopg.sql`/`urllib.parse` and use the components
- If `DATABASE_URL` is not set, fall back to the 5 individual vars (for backward compat during transition)
- Remove any language suggesting values come from a file

The `render_sql()` and `get_connection()` functions should work unchanged — only the env-loading logic changes.

### 2. `SKILL.md` (connect skill)

In the "Dependencies" / "Bootstrap Environment Variables" section:
- Replace the list of 5 separate env vars with: `DATABASE_URL` (required if not using individual vars; format: `postgres://username:password@host:port/dbname`)
- Add individual vars as optional fallback with a note that `DATABASE_URL` takes precedence
- Remove: "Set these in the operator's shell profile or in `~/.config/united_agent/.env`"
- Change framing to: "The calling agent/client provides `DATABASE_URL` at runtime"
- Quickstart: show `export DATABASE_URL=postgres://...` instead of 5 separate exports
- Keep all existing script documentation and flow descriptions

### 3. `README.md`

In the "For Normal Users" and "For Server Deployment" sections:
- Replace the 5 `export AGENT_KB_DB_*` lines with a single `export DATABASE_URL=postgres://postgres:postgres@localhost:5432/united_agent`
- No other structural changes to README (previous task already restructured it)

### 4. Existing scripts (`verify_connection.py`, `validate_post_flow.py`, `validate_review_flow.py`, `list_content.py`)

These all import `get_connection()` from `_postgres_connect_common.py`. No changes needed to these files — the change is entirely in the common helper.

## Non-goals

- Do not change `docs/developer-guide.md` or `docs/design-philosophy.md`
- Do not change any SQL files
- Do not change any test files (tests that assert env var names may need updating — see below)
- Do not add file-based credential storage of any kind
- Do not change the connection behavior — same Postgres connection, same RLS enforcement

## Backward Compatibility

Individual `AGENT_KB_DB_*` vars should still work as fallback if `DATABASE_URL` is not set. This lets existing callers transition gradually.

## Test Impact

- `tests/test_postgres_connect_tooling.py` has `test_connect_common_helper_uses_env_defaults_and_identity_query` which may assert the individual env var names. Check and update if needed.
- Live flow tests use `live_db_env()` — verify they set `DATABASE_URL` or individual vars correctly.

## Acceptance

- `DATABASE_URL` env var is the primary way to configure the connection
- A single `export DATABASE_URL=postgres://postgres:postgres@localhost:5432/united_agent` works for both "For Normal Users" and "For Server Deployment" sections in README
- SKILL.md no longer mentions shell profiles, `.env` files, or file-based storage
- SKILL.md states clearly: "the calling agent/client provides `DATABASE_URL` at runtime"
- All existing tests pass (25 in tooling + live flows)
- The `_postgres_connect_common.py` helper parses `DATABASE_URL` correctly with `urllib.parse`
