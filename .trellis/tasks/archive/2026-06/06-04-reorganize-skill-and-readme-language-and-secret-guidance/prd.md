# Reorganize Skill And README Language And Secret Guidance

## Goal

Make the distributed docs say the same thing, in the same voice, about two operational facts: how the first privileged operator is bootstrapped, and how agents should supply database credentials and new-account passwords at runtime without persisting them in repo files.

## What I already know

- `README.md` currently claims the first `super_admin` can be created with `create_principal.py --global-role super_admin`, but that script only accepts `normal_user` and `admin`.
- The real bootstrap path today is in `postgres/init/001-united-agent.sql`, which seeds the local `postgres` login into `auth.accounts` and grants it `super_admin`.
- `skills/agent-kb-postgres-connect/SKILL.md` already says the calling agent/client provides `DATABASE_URL` at runtime and the skill never stores credentials to disk.
- `skills/agent-kb-postgres-admin/SKILL.md` still uses older wording about shell profiles / `~/.config/united_agent/.env`, which is inconsistent with the connect skill and with the recent move toward caller-provided runtime env.
- Admin account creation accepts `--new-password` or `AGENT_KB_NEW_PRINCIPAL_PASSWORD`; password storage is delegated to PostgreSQL role creation, not to an app-level password table.
- The user wants the language in the skills and README reorganized, and wants stronger guidance telling agents to keep secrets in agent-provided env rather than in checked-in files.

## Assumptions (temporary)

- This task is primarily a docs/wording cleanup, not a new bootstrap automation feature.
- We should describe the current bootstrap truth first, then show the supported ongoing admin flows.
- We should avoid recommending `~/.config/united_agent/.env` if the preferred model is agent-runtime env injection.

## Open Questions

- None.

## Requirements (evolving)

- README must stop claiming `create_principal.py` can create a `super_admin`.
- README must explain that initialization directly seeds the local `postgres` operator with `super_admin` and that this is the current bootstrap path.
- README and both skill docs must use one consistent message for secret handling: the caller/agent injects env at runtime; the skill reads from `os.environ`; the skill does not persist secrets.
- README and both skill docs must explicitly tell operators to use their own agent tool's `.env` / secret-injection mechanism to provide runtime env, rather than checking secrets into repo files or editing shipped skill files.
- Admin docs must clearly explain the distinction between bootstrap identity and ordinary admin-created accounts.
- Docs should make the preferred runtime secret path obvious to agents.
- This task is docs-only; no new bootstrap automation flow is required.
- README should be primarily Chinese.
- `SKILL.md` files should remain English.
- Secret guidance should use a general rule plus a short example of using the operator's own agent tool `.env` / secret configuration, without naming specific tools.

## Acceptance Criteria (evolving)

- [ ] README no longer documents an impossible `create_principal.py --global-role super_admin` flow.
- [ ] README explains the current first-operator bootstrap path accurately.
- [ ] `agent-kb-postgres-connect/SKILL.md` and `agent-kb-postgres-admin/SKILL.md` present a consistent runtime-env secret model.
- [ ] Docs explicitly steer agents to use agent-tool/runtime env for `DATABASE_URL` and new principal passwords.
- [ ] README and both skill docs are materially rewritten for clarity instead of receiving only tiny patch wording.

## Definition of Done (team quality bar)

- Tests added/updated where doc contracts are asserted
- Lint / typecheck / CI green where applicable
- Docs updated consistently across README and shipped skills
- Rollout/rollback considered if risky

## Out of Scope (explicit)

- Changing database password hashing/storage behavior
- Adding a new API server or UI for secret management
- Broad auth model redesign or new bootstrap automation

## Technical Notes

- Files inspected: `README.md`, `skills/agent-kb-postgres-connect/SKILL.md`, `skills/agent-kb-postgres-admin/SKILL.md`, `skills/agent-kb-postgres-admin/scripts/create_principal.py`, `skills/agent-kb-postgres-admin/scripts/sql/create_principal.sql`, `postgres/init/001-united-agent.sql`.
- Recent archived task `06-03-switch-connect-skill-env-from-file-based-vars-to-caller-provided-uri` already established the intended framing: caller-provided runtime env, not file-based storage.
- User-approved direction: document the existing bootstrap truth (`postgres` is seeded as `super_admin` during init) and rewrite the docs/skills to emphasize secret management through each agent tool's own `.env` / runtime env facility.
- User-approved language split: README in Chinese; skills remain in English.
- User-approved guidance style: general principle first, then a short example; do not enumerate specific agent tools.
