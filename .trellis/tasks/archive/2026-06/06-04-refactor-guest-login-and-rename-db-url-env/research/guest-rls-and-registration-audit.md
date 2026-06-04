# Research: Guest RLS and Registration Audit

- **Query**: Current state of guest login, RLS policies, user registration flow, and DB URL env naming
- **Scope**: internal
- **Date**: 2026-06-04

## Findings

### 1. Guest Account Architecture

The guest account is a **hardcoded PostgreSQL LOGIN role** with password `'guest'`, created during schema bootstrap in `postgres/init/001-united-agent.sql` (lines 1056-1084).

**Creation flow** (lines 1058-1076):
```sql
-- Guest 账户：用于匿名 token 注册。guest 是 normal_user，继承读权限，但写操作被 RLS 拦掉。
-- guest 必须能被 register_with_token 的 SECURITY DEFINER 调用，所以是 LOGIN 账号。
IF to_regrole('guest') IS NULL THEN
  CREATE ROLE guest LOGIN PASSWORD 'guest';
END IF;
GRANT united_agent_user TO guest;

INSERT INTO auth.accounts (principal_type, display_name, pg_login_role, account_status)
VALUES ('agent', 'Guest', 'guest', 'active')
ON CONFLICT (pg_login_role) DO NOTHING;

INSERT INTO auth.principal_global_roles (account_id, role_name, granted_by)
SELECT id, 'normal_user', id
FROM auth.accounts WHERE pg_login_role = 'guest'
ON CONFLICT (account_id, role_name) DO NOTHING;
```

**Guest's identity model**:
- `auth.accounts` row: `principal_type = 'agent'`, `display_name = 'Guest'`, `account_status = 'active'`
- Global role: `normal_user` (via `auth.principal_global_roles`)
- Runtime role membership: `united_agent_user`
- Identity resolved via `session_user` → `auth.current_account_id()` (line 151-160)

**`auth.is_guest()` function** (lines 209-221):
```sql
CREATE FUNCTION auth.is_guest() RETURNS boolean
LANGUAGE sql STABLE SECURITY DEFINER
SET search_path = auth, pg_catalog
AS $$
  SELECT EXISTS (
    SELECT 1 FROM auth.accounts AS a
    WHERE a.pg_login_role = session_user
      AND a.pg_login_role = 'guest'
  );
$$;
```

**Guest permissions** (lines 1082-1084):
```sql
-- Guest 只能读，写操作由 RLS 拦掉（NOT auth.is_guest() 在各写策略中）。
GRANT SELECT ON ALL TABLES IN SCHEMA app TO guest;
GRANT SELECT ON ALL TABLES IN SCHEMA auth TO guest;
```

**Key observation**: Guest has `SELECT` on every table in both schemas, but NO INSERT/UPDATE/DELETE grants. Write operations are blocked at both the GRANT level (no explicit INSERT/UPDATE/DELETE grants to `guest`) and the RLS level (every write policy includes `NOT auth.is_guest()`).

**Registration function grant** (line 1078-1080):
```sql
-- token 注册入口允许未映射到 auth.accounts 的低权限 PostgreSQL login 调用；
-- 真正的建号边界仍由 token 本身控制。
-- 注意：register_with_token 内部已加了 is_guest() 检查，确保只有 guest 账号才能调用。
GRANT EXECUTE ON FUNCTION auth.register_with_token(text, auth.principal_type, text, text, text) TO PUBLIC;
```

**Critical design fact**: `register_with_token` is granted to `PUBLIC`, meaning ANY PostgreSQL login can theoretically call it. However, the function itself has a `auth.is_guest()` guard (line 425), so effectively only `guest` can use it. The comment on line 1078 says the intent is to allow "a low-permission PostgreSQL login not mapped to auth.accounts" to call it, but the reality is the `is_guest()` check requires the caller to map to the specific `guest` account.

**Hardcoded password concern**: The guest password `'guest'` is hardcoded in the SQL init file. The README.md (line 49) and SKILL.md (line 83, 111) both document using `postgres://guest:guest@<HOST>:5432/united_agent` for registration.

---

### 2. RLS Policies — Guest Blocking Pattern

All 31 RLS policies (lines 772-993) target the `united_agent_user` role. Guest is excluded from writes via `NOT auth.is_guest()` in every INSERT/UPDATE/DELETE policy. SELECT policies are generally open (`USING (true)` or `USING (id = auth.current_account_id() OR auth.is_admin())`), meaning guest can read everything.

**Tables with RLS + FORCE RLS** (lines 750-769):

| Table | RLS | FORCE |
|---|---|---|
| `auth.accounts` | ✅ | ✅ |
| `auth.principal_global_roles` | ✅ | ✅ |
| `auth.registration_tokens` | ✅ | ✅ |
| `auth.board_moderators` | ✅ | ✅ |
| `app.boards` | ✅ | ✅ |
| `app.posts` | ✅ | ✅ |
| `app.review_entries` | ✅ | ✅ |
| `app.review_history` | ✅ | ✅ |
| `app.tags` | ✅ | ✅ |
| `app.post_tags` | ✅ | ✅ |

**Policies with explicit `NOT auth.is_guest()` guards**:

| Policy | Line | Operation | Table |
|---|---|---|---|
| `accounts_update_admin` | 778-779 | UPDATE | auth.accounts |
| `accounts_insert_admin` | 783 | INSERT | auth.accounts |
| `accounts_delete_admin` | 787 | DELETE | auth.accounts |
| `principal_global_roles_insert_admin_normal_user` | 803 | INSERT | auth.principal_global_roles |
| `posts_insert_authenticated` | 850 | INSERT | app.posts |
| `review_entries_insert_own` | 880 | INSERT | app.review_entries |
| `review_entries_update_own` | 884-885 | UPDATE | app.review_entries |

**Policies WITHOUT explicit `NOT auth.is_guest()` but still block guest** (via `auth.can_write()` or `auth.is_admin()` which implicitly fail for guest because guest cannot write and is not admin):

- `boards_insert_admin` (line 830) — requires `auth.is_admin()`
- `boards_update_admin` (line 834) — requires `auth.can_write() AND auth.is_admin()`
- `posts_update_verification` (line 866) — requires `auth.can_moderate_board()` which calls `auth.can_write()`
- `tags_insert_moderator_or_admin` (line 917) — requires `auth.can_write()`
- `post_tags_insert_author_or_moderator` (line 952) — requires `auth.can_write()`
- All `registration_tokens_*` policies (lines 982-993) — require `auth.can_write() AND auth.is_admin()`

**`auth.can_write()` guard** (lines 253-261): requires `auth.current_account_id() IS NOT NULL AND account_status = 'active'`. Since guest IS active and has a valid account_id, `auth.can_write()` returns `true` for guest. This means policies that only check `auth.can_write()` (without `NOT auth.is_guest()`) could theoretically allow guest writes — BUT guest has no explicit INSERT/UPDATE/DELETE GRANTs on the tables, so PostgreSQL prevents it at the permission level before RLS even fires.

---

### 3. Registration Flow — End-to-End

#### 3.1 Token Creation (Admin Path)

**Script**: `skills/agent-kb-postgres-admin/scripts/manage_registration_token.py`

- Only `admin` or `super_admin` can create tokens
- Runs as admin session (using `AGENT_KB_DATABASE_URL` with admin credentials)
- Generates `secrets.token_urlsafe(24)`, hashes with SHA-256, stores hash + preview
- Options: `--max-uses` (required), `--expires-at` (optional)
- Token printed to stdout after creation

**SQL function**: `auth.issue_registration_token()` (lines 351-400)
- Validates caller is admin via `auth.can_write() AND auth.is_admin()`
- Inserts into `auth.registration_tokens` table

#### 3.2 Token Consumption (Guest Path)

**Script**: `skills/agent-kb-postgres-connect/scripts/register_with_token.py`

- Connects as `guest` (uses `AGENT_KB_DATABASE_URL=postgres://guest:guest@...`)
- Hashes token client-side: `hashlib.sha256(args.token.encode("utf-8")).hexdigest()`
- Calls `auth.register_with_token(token_hash, principal_type, display_name, login_role, password)`
- Password comes from `--new-password-env` (reads named env var, e.g. `AGENT_KB_NEW_PASSWORD`)

**SQL function**: `auth.register_with_token()` (lines 402-489)
- Guard: `IF NOT auth.is_guest()` → "registration via token is only allowed for the guest account" (line 425)
- Token validation: exists, not revoked, not expired, has remaining uses (lines 433-453)
- Creates PostgreSQL login role via `auth.create_account_login_unchecked()` (line 454)
- Inserts into `auth.accounts` with `account_status = 'active'` (lines 456-458)
- Grants `normal_user` role in `auth.principal_global_roles` (lines 460-462)
- Increments `uses_consumed` on the token (lines 464-469)
- On error, drops the created PostgreSQL role if it exists (lines 482-487)

#### 3.3 Registration Token Table Schema

From `postgres/init/001-united-agent.sql` lines 50-61:
```sql
CREATE TABLE auth.registration_tokens (
  id bigserial PRIMARY KEY,
  token_hash text NOT NULL UNIQUE,
  token_preview text NOT NULL,
  max_uses integer NOT NULL CHECK (max_uses > 0),
  uses_consumed integer NOT NULL DEFAULT 0 CHECK (uses_consumed >= 0 AND uses_consumed <= max_uses),
  expires_at timestamptz,
  revoked_at timestamptz,
  last_used_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now(),
  created_by bigint REFERENCES auth.accounts(id) ON DELETE SET NULL
);
```

#### 3.4 Test Coverage

In `tests/test_registration_token_live_flows.py` (line 110-111):
```python
registration_login = self.make_login_role("registration_guest")
registration_password = f"pw_{self.suffix}_registration_guest"
```
The test creates a temporary `registration_guest` role (not the built-in `guest`), suggesting the test isolates the registration flow from the built-in guest account. This is worth noting for refactoring — the existing test pattern may need updating if the guest mechanism changes.

---

### 4. Database URL Environment Variable Naming

#### 4.1 Current Convention

The **current single env var** is `AGENT_KB_DATABASE_URL`. This is the only env var accepted across all skill scripts.

**Connect skill** (`_postgres_connect_common.py` lines 38-57):
```python
def db_env(url_from_flag: str | None = None) -> dict[str, str]:
    if url_from_flag:
        u = urlsplit(url_from_flag)
        # ... parse components
    if os.environ.get("AGENT_KB_DATABASE_URL"):
        u = urlsplit(os.environ["AGENT_KB_DATABASE_URL"])
        # ... parse components
    raise SystemExit("database URL is required (set AGENT_KB_DATABASE_URL or use --url)")
```

**Admin skill** (`_postgres_admin_common.py` lines 28-29):
```python
def database_url() -> str:
    return require_env("AGENT_KB_DATABASE_URL")
```

#### 4.2 Files Referencing `AGENT_KB_DATABASE_URL`

| File | Context |
|---|---|
| `skills/agent-kb-postgres-connect/scripts/_postgres_connect_common.py:48-49` | Primary connection logic |
| `skills/agent-kb-postgres-admin/scripts/_postgres_admin_common.py:28-29` | Admin connection logic |
| `skills/agent-kb-postgres-connect/SKILL.md:76,86-87` | User-facing docs |
| `skills/agent-kb-postgres-admin/SKILL.md:34-35,41,87` | Admin-facing docs |
| `README.md:16,38,41,46,49,127` | Project README |
| `docs/developer-guide.md:42,45,50-51,149` | Developer guide |
| `.trellis/spec/backend/database-guidelines.md:97,111,129,498-499` | Spec/contract docs |
| `tests/test_board_post_live_flows.py:22,25` | Live flow tests |
| `tests/test_connect_skill_live_flows.py:25,28,159,234,255` | Live flow tests |
| `tests/live_postgres_helpers.py:26,29,42,201` | Test helpers |
| `tests/test_agent_kb_postgres_skeleton.py:202` | Static schema test |
| `tests/test_postgres_admin_tooling.py:73-74,77,144-145,184,201,207` | Admin tooling tests |
| `tests/test_postgres_connect_tooling.py:104,119-120,143,161,172,175` | Connect tooling tests |

Total: **99 occurrences** of `AGENT_KB_DATABASE_URL` across the codebase.

#### 4.3 Historical Naming Evolution

Based on journal entries and archived PRDs:

1. **Originally**: 5 separate env vars (`AGENT_KB_DB_HOST`, `AGENT_KB_DB_PORT`, etc.) — Session 23
2. **Transitioned to `DATABASE_URL`**: Session 23 switched connect skill to `DATABASE_URL` URI format, with individual vars as fallback
3. **Admin helpers made `DATABASE_URL`-only**: Session 31 removed legacy compatibility and required `DATABASE_URL`
4. **Renamed to `AGENT_KB_DATABASE_URL`**: At some point the name was prefixed with `AGENT_KB_` to namespace it (likely to avoid conflict with generic `DATABASE_URL` used by other tools)

**Critical note**: The archived task `06-04-fix-admin-script-env-var-contract/prd.md` (line 30) states: "User-facing admin usage must rely on `DATABASE_URL` as the only database connection env." But the current codebase uses `AGENT_KB_DATABASE_URL` everywhere. There is a tension between the historical intent and current state.

#### 4.4 All Currently Active Env Vars

| Env Var | Purpose | Where Used |
|---|---|---|
| `AGENT_KB_DATABASE_URL` | Database connection (primary, required) | All scripts |
| `AGENT_KB_NEW_PRINCIPAL_PASSWORD` | New account password (legacy fallback for `create_principal.py`) | Admin skill |
| `AGENT_KB_NEW_PASSWORD` | Documented as example name for `--new-password-env` flag | Various scripts |

No other `DB_URL*`, `DATABASE_URL*`, `POSTGRES_URL*`, or `DSN*` patterns exist in the current codebase.

---

### 5. Existing PRD / Planning Docs

- No `prd.md` exists in the current task directory (`.trellis/tasks/06-04-refactor-guest-login-and-rename-db-url-env/`)
- `task.json` shows status=`planning`, priority=`P2`, no description or related files set
- `implement.jsonl` only has the seed `_example` row (not yet curated)
- `check.jsonl` only has the seed `_example` row (not yet curated)

**Related archived tasks** providing historical context:
- `06-04-registration-flow/prd.md` — Introduced the single-use anonymous registration token concept
- `06-04-fix-admin-script-env-var-contract/prd.md` — Made admin helpers use `DATABASE_URL` only
- `06-03-switch-connect-skill-env-from-file-based-vars-to-caller-provided-uri/prd.md` — Switched from 5 separate vars to single URI

---

### 6. Files Found

| File Path | Description |
|---|---|
| `postgres/init/001-united-agent.sql` | All schema, RLS, auth functions, and guest account bootstrap |
| `skills/agent-kb-postgres-connect/scripts/register_with_token.py` | Registration script (guest-side) |
| `skills/agent-kb-postgres-connect/scripts/_postgres_connect_common.py` | Connect skill DB connection logic |
| `skills/agent-kb-postgres-admin/scripts/_postgres_admin_common.py` | Admin skill DB connection logic |
| `skills/agent-kb-postgres-admin/scripts/manage_registration_token.py` | Token creation/management (admin-side) |
| `skills/agent-kb-postgres-connect/SKILL.md` | Connect skill docs (guest/registration usage) |
| `skills/agent-kb-postgres-admin/SKILL.md` | Admin skill docs |
| `README.md` | Project README (guest connection examples) |
| `docs/developer-guide.md` | Developer guide (connection and registration docs) |
| `.trellis/spec/backend/database-guidelines.md` | Spec: database guidelines (env var contracts) |
| `tests/test_registration_token_live_flows.py` | Live integration test for registration |
| `tests/test_postgres_connect_tooling.py` | Tooling test verifying guest/guest references |
| `tests/test_agent_kb_postgres_skeleton.py` | Static schema test verifying is_guest() in RLS |
| `.trellis/tasks/archive/2026-06/06-04-registration-flow/prd.md` | Archived PRD: registration flow design |
| `.trellis/tasks/archive/2026-06/06-04-fix-admin-script-env-var-contract/prd.md` | Archived PRD: env var contract fix |

### 7. Key Architectural Observations

1. **Guest is the only registration entrypoint**: The entire registration flow is gated behind the `guest` account. To register, a new user must connect as `guest` with a valid token. After registration, they connect as their own login.

2. **Guest has read-only access to everything**: SELECT on all tables in both schemas. This means guest can see all boards, posts, reviews, tags, and even account information — a broad read surface.

3. **Guest password is hardcoded**: The password `'guest'` is in plaintext in the SQL init file. For production, this would need to be overridden, but the bootstrap creates it unconditionally.

4. **`register_with_token` is PUBLIC but guarded**: Granted to PUBLIC but has internal `is_guest()` check. This means if someone has a different login with `EXECUTE` on the function, they still can't use it unless they match the guest check.

5. **Two layers of write blocking for guest**: (a) No explicit INSERT/UPDATE/DELETE GRANTs to the `guest` role on any table, (b) RLS policies include `NOT auth.is_guest()` in write paths. The first layer (GRANT) is the primary defense; RLS is a secondary safety net.

6. **`auth.can_write()` returns `true` for guest**: Because guest is `active` and has a valid `auth.accounts` row. This means policies that check only `auth.can_write()` (without `NOT auth.is_guest()` and without `auth.is_admin()`) technically allow guest through the RLS layer — but the GRANT layer blocks it first.

7. **`AGENT_KB_DATABASE_URL` is the sole connection env**: Used by 99 references across all skill scripts, tests, docs, and specs. No fallback to generic `DATABASE_URL` exists in current code.

## Caveats / Not Found

- No explicit "rename" decision has been documented — the current PRD is empty, so the intended target name for the env var is unclear
- The `FORCE ROW LEVEL SECURITY` on all tables means even table owners are subject to RLS (unusual)
- The `register_with_token` comment (line 1078) says it allows "low-permission login not mapped to auth.accounts" but the code only allows `guest` (which IS mapped to auth.accounts) — this is a doc/code mismatch that may be intentional
- Live flow tests create a temporary `registration_guest` role rather than using the built-in `guest` — this may be for test isolation but suggests the test pattern is decoupled from the actual guest mechanism
