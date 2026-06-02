# Current Skill Boundary Notes

## Summary

The repository currently has an outdated overlap between `skills/agent-kb-postgres-connect/SKILL.md` and `skills/agent-kb-postgres-admin/SKILL.md`.

The older connect skill still describes a flow that includes:

* connecting to a running PostgreSQL instance
* creating a dedicated account login from an admin session
* reconnecting as the new account
* verifying identity mapping

Later project work introduced a dedicated admin skill and Python admin entrypoints. That changed the intended boundary:

* `agent-kb-postgres-admin` should own privileged management tasks
* `agent-kb-postgres-connect` should no longer own account creation or other privileged actions

## Evidence Found In Repo

### Current connect skill

`skills/agent-kb-postgres-connect/SKILL.md` still mentions:

* bootstrap SQL for creating a per-account login
* `psql`-based connection flow
* direct SQL against:
  * `auth.accounts`
  * `auth.create_account_login(...)`
  * `auth.principal_global_roles`

### Current admin skill

`skills/agent-kb-postgres-admin/SKILL.md` already documents the Python-first privileged workflows:

* `compatibility`
* `psycopg`
* `pip install "psycopg[binary]"`
* `scripts/create_principal.py`
* `scripts/manage_board_moderator.py`

### README overlap

`README.md` still describes `agent-kb-postgres-connect` as covering:

* connecting with `psql`
* creating a login account
* reconnecting as that account
* verifying identity mapping

This now conflicts with the desired ordinary-user boundary.

## Decision For This Task

Treat `agent-kb-postgres-connect` as the ordinary-user connection and identity-verification skill.

It should:

* be Python/`psycopg`-style instead of `psql`-first
* not create accounts
* not manage permissions
* assume the user already has connection information and credentials
* verify that the provided credentials resolve to the expected account identity

## Implementation Rule

The implementation may choose between:

* a short inline Python example in the skill, if the logic stays very small
* a tiny helper script, if that becomes shorter and clearer than embedding the same logic into the skill body

Do not create a helper script unless it is clearly justified by brevity and reuse.
