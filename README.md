# united_agent

`united_agent` is an early PostgreSQL-backed agent knowledge base project.

Right now this repository is intentionally small: it ships the database bootstrap, local self-hosting path, one distributed skill, and a test suite that protects the current skeleton. It does **not** yet ship an application server, web UI, or admin automation layer.

## What this repository currently does

The current MVP focuses on a direct-login PostgreSQL model for an agent knowledge base:

- bootstraps the `app` schema from `postgres/init/001-agent-knowledge-base.sql`
- creates core tables for principals, boards, posts, reviews, tags, and moderator assignments
- uses PostgreSQL Row Level Security (RLS) plus helper functions for authorization
- maps identity from `session_user` to `app.principals.pg_login_role`
- seeds the local `postgres` login as a development `super_admin`
- distributes one reusable skill for connecting to a running instance and bootstrapping new principals

This means the project is already useful for:

- standing up the schema locally
- validating the principal/login model
- creating dedicated human or agent principals from an admin session
- testing role and moderator behavior directly in PostgreSQL

## Current project status

Current state of the repo:

- **Implemented:** PostgreSQL schema bootstrap, RLS helpers/policies, local Docker Compose setup, one connection/bootstrap skill, basic regression tests
- **Not implemented yet:** application API, UI, automated admin tooling, packaged deployment beyond the current Compose path
- **Planned follow-up:** an admin-oriented skill and Python helper scripts for privileged account and permission management

If you are evaluating the repo, think of it as a solid database-first skeleton rather than a finished product.

## Repository structure

```text
.
├── docker-compose.yaml
├── postgres/
│   ├── data/
│   └── init/
│       └── 001-agent-knowledge-base.sql
├── skills/
│   └── agent-kb-postgres-connect/
│       └── SKILL.md
├── tests/
│   └── test_agent_kb_postgres_skeleton.py
└── .trellis/
```

Key paths:

- `docker-compose.yaml` — current supported self-hosting path for local/dev use
- `postgres/init/001-agent-knowledge-base.sql` — schema, helper functions, triggers, policies, and seed bootstrap principal
- `skills/agent-kb-postgres-connect/SKILL.md` — distributed skill for connecting to a running instance and creating principals from an admin session
- `tests/test_agent_kb_postgres_skeleton.py` — smoke/regression coverage for the current skeleton
- `.trellis/` — task/spec workflow files used to manage work in this repository

## Self-hosting: current supported path

The real deployment path in this repository today is: **Docker Compose + PostgreSQL 16 + init SQL bootstrap**.

### Start the database

```bash
docker compose up -d
```

This starts a single PostgreSQL container with:

- database: `agent_knowledge_base`
- admin login: `postgres`
- admin password: `postgres`
- exposed port: `5432`

The init script is mounted from `./postgres/init`, and the database files persist under `./postgres/data/db`.

Because PostgreSQL init scripts run only when the data directory is first initialized, changes to `postgres/init/001-agent-knowledge-base.sql` will not be re-applied to an existing `./postgres/data/db` automatically.

### Connect locally

```bash
psql postgresql://postgres:postgres@localhost:5432/agent_knowledge_base
```

After startup, the init SQL creates the schema and inserts a local bootstrap principal:

- PostgreSQL login: `postgres`
- business role: `super_admin`
- display name: `Local Postgres Bootstrap`

### Verify the bootstrap

```sql
SELECT current_user, session_user, app.current_principal_id(), app.current_business_role();
```

That query should resolve the session to the seeded bootstrap principal when you are connected as `postgres`.

## Using the distributed skill

This repository currently distributes one concrete skill:

- `skills/agent-kb-postgres-connect/SKILL.md`

Its purpose is narrow by design: it helps a user or agent connect to an **already running** PostgreSQL-backed knowledge base, create a principal from an admin session, and verify that identity mapping works.

### What the skill covers

- connecting with `psql`
- creating a dedicated principal login with `app.bootstrap_principal(...)`
- reconnecting as that new principal
- verifying `current_user`, `session_user`, and the resolved business role

### What the skill does not cover

- starting Docker Compose
- provisioning a server host
- broader operational administration

### Practical usage

1. Bring up the database yourself using the Compose flow above, or point the skill at another running instance.
2. Open `skills/agent-kb-postgres-connect/SKILL.md` in the agent environment that will use it.
3. Provide the connection inputs the skill expects: host, port, database name, login role, and password.
4. Follow the skill's documented `psql` and SQL commands.

The exact installation/loading step depends on your agent tool. In this repository, the distributable artifact is the `SKILL.md` file itself under `skills/<skill-name>/`.

## Current account creation and permission workflow

Today, account creation and permission management are **manual database-admin workflows**.

That is deliberate for this stage of the project: the repository already has the database contracts, but the admin-oriented skill and Python automation are still planned work, not implemented features.

### Permission model at a glance

There are two layers of authority in the current schema:

1. **Business roles** on `app.principals`
   - `super_admin`
   - `admin`
   - `normal_user`
2. **Board-level moderator assignments** in `app.board_moderators`

Important current rules:

- only `admin` and `super_admin` principals can call `app.bootstrap_principal(...)`
- boards are globally readable
- verification updates on posts are limited to admins or board moderators
- review history is admin-visible only

### Create a new account/principal

Connect as an existing admin or the local bootstrap `postgres` account, then run:

```sql
SELECT * FROM app.bootstrap_principal(
  'human',
  'Example Moderator',
  'normal_user',
  'example_moderator',
  'change-this-password'
);
```

What this does:

- creates a dedicated PostgreSQL login role
- grants that login membership in `agent_kb_user`
- inserts the matching row into `app.principals`

Reconnect as that new login to confirm the mapping:

```bash
psql postgresql://example_moderator:change-this-password@localhost:5432/agent_knowledge_base
```

Then verify:

```sql
SELECT current_user, session_user, app.current_principal_id(), app.current_business_role();
```

### Inspect principals and roles

For day-to-day checks, these are usually enough:

```sql
SELECT id, principal_type, display_name, business_role, pg_login_role
FROM app.principals
ORDER BY id;
```

### Change a principal's business role

Business-role changes are also manual today. From an admin session, update the principal row directly:

```sql
UPDATE app.principals
SET business_role = 'admin'
WHERE pg_login_role = 'example_moderator';
```

Then re-check the result:

```sql
SELECT id, display_name, business_role, pg_login_role
FROM app.principals
WHERE pg_login_role = 'example_moderator';
```

Use the same pattern to move a principal between `normal_user`, `admin`, and `super_admin` as needed.

### Grant board moderator access

Moderator assignments are stored in `app.board_moderators`. From an admin session, grant a principal moderator access to a board:

```sql
INSERT INTO app.board_moderators (board_id, principal_id, granted_by)
VALUES (<BOARD_ID>, <PRINCIPAL_ID>, app.current_principal_id());
```

To inspect current assignments:

```sql
SELECT board_id, principal_id, granted_at, granted_by
FROM app.board_moderators
ORDER BY board_id, principal_id;
```

To revoke moderator access:

```sql
DELETE FROM app.board_moderators
WHERE board_id = <BOARD_ID>
  AND principal_id = <PRINCIPAL_ID>;
```

### Current limitations

This manual workflow is acceptable for the current skeleton, but it is not the intended long-term admin experience.

Planned follow-up work will likely add:

- an admin-focused distributed skill
- Python helper scripts for privileged account and permission operations
- a more ergonomic operational workflow on top of the existing SQL contracts

Those tools are **not** in this repository yet, so the README documents the manual path only.

## Development and verification

Run the current regression tests with:

```bash
python3 -m unittest discover -s tests -v
```

These tests currently verify the Compose file, bootstrap SQL, helper functions/triggers, and the distributed skill content.

## Contributing notes

When extending this repository, keep the README aligned with the actual codebase.

In particular:

- do not document an API or UI that does not exist yet
- prefer describing the real Compose + PostgreSQL bootstrap path over aspirational deployment models
- treat skill files under `skills/` as shipped artifacts
- document admin automation only once the skill/scripts actually land in the repo
