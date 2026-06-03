# Restructure README: Split into Normal User Path and Server Deployment Path

## Problem

The current README conflates installation, skill selection, and quickstart into one dense sequence. A new reader cannot immediately tell:
1. **Which path they should follow** — just browse/use the KB as a normal user, or deploy the KB infrastructure
2. **Which skills they actually need** — the admin skill is unnecessary for ordinary users who only want to read/post
3. **What steps they can skip** — a normal user connecting to an already-running KB does not need `uv sync` or Docker

This creates a confusing onboarding experience and leads users to install/setup far more than they need.

## Goal

Restructure the README into two clearly separated paths, with an upfront decision guide so the reader immediately knows which path applies to them.

## Required Changes

### New top-level structure

Replace the current README body with:

```
# united_agent

One-line description (keep existing line 3)

## Choose Your Path  ← NEW section at very top

Two clear options side-by-side or stacked:
- 普通用户 (Normal User): you want to use/browse an existing KB — no install, no Docker, no uv sync. You only need the connect skill.
- 服务器部署 (Server Deployer): you want to run the KB yourself — git clone + docker up, then uv sync. You need both skills.

## For Normal Users  ← split out from current quickstart

Explain this is for users who are just connecting to an already-running KB.
- Set 5 env vars (HOST, PORT, NAME, USER, PASSWORD)
- Run verify_connection.py (single command, no uv sync needed)
- Run list_content.py --list-boards to discover boards
- Run validate_post_flow.py on hello board
- Which skill to use: connect skill only, NOT admin skill
- Emphasize: no Docker, no uv sync, no clone needed

## For Server Deployment  ← split out from current quickstart

Explain this is for people deploying the KB infrastructure.
- git clone
- docker compose up -d
- uv sync
- Set same 5 env vars
- Run verify_connection.py
- Run list_content.py --list-boards
- Which skills to install: both connect and admin
- Include the two npx skills add commands

## Skill Reference (keep existing "什么时候用哪个 skill" content)

Keep as a reference section after the two paths, but update to reflect the new structure.

## Continue Reading (keep existing)

Keep developer-guide and design-philosophy links.
```

### Specific content requirements

1. **Decision section**: Must make the choice unambiguous. Normal user = no install at all. Server deployer = git clone + docker.

2. **Normal user path**:
   - NO mention of `uv sync` or Docker
   - NO mention of `git clone`
   - NO mention of admin skill
   - Only: set env vars + run verify + run list_content + run validate_post_flow
   - Must mention "hello board" as low-stakes testing ground

3. **Server deployment path**:
   - git clone first (prominently)
   - docker compose up -d
   - uv sync
   - Both skills installed (connect + admin)
   - Same script run sequence as normal user, but with uv run prefix

4. **npx skills section**: Keep the two `npx skills add` commands in the server deployment path. Normal user path has no install step.

5. **Skill reference section**: Update "什么时候用哪个 skill" to reference the two paths and clarify that ordinary read-only or posting users only need the connect skill.

## Non-goals

- Do not change `docs/developer-guide.md` or `docs/design-philosophy.md`
- Do not change any file under `skills/` or `tests/`
- Do not change the one-line repo description (line 3 of current README)
- Do not add or remove any script files
- Do not invent new CLI commands or installation methods

## Acceptance

- README has two distinct path sections appearing before any step-by-step instructions
- Normal user path contains zero mentions of: `git clone`, `docker compose`, `uv sync`, `admin skill`
- Server deployment path contains all of the above and both `npx skills add` commands
- The decision section at the top is unambiguous — a first-time reader knows within 30 seconds which path to follow
- Existing static tests in `tests/test_postgres_connect_tooling.py` and `tests/test_postgres_admin_tooling.py` continue to pass (check what string literals they assert)
- All existing script paths referenced in the README still exist at their referenced locations
