# Fix Connect Syntax Error And Skill Install Command

## Goal

Fix the reported connect-side syntax issue and correct the documented `npx skills add` install command so the shipped docs and skill entry guidance match the real install path and working syntax.

## What I already know

- The user reports two concrete issues: a syntax error in "connect" and an incorrect install command.
- `README.md` currently documents install commands as `npx skills add jerry-harm/united_agent --skill ...`.
- The user expects the install form `npx skills add jerry-harm/united_agent/skills --skill agent-kb-postgres-admin` and, by implication, the same `/skills` path for connect.
- `skills/agent-kb-postgres-connect/scripts/*.py` passes `python3 -m py_compile`, so the reported connect syntax error is not a Python parser error in those shipped scripts.
- The user supplied the concrete GitHub parse error: `Error in user YAML: (<unknown>): mapping values are not allowed in this context at line 2 column 381`.
- That error matches the current `skills/agent-kb-postgres-connect/SKILL.md` frontmatter, where the long unquoted `description:` line contains another colon (`Also covers:`), which breaks YAML parsing on GitHub.

## Assumptions (temporary)

- The install-command fix should likely apply anywhere the docs mention `npx skills add` for these two shipped skills.
- The connect syntax fix is a YAML-frontmatter repair in `skills/agent-kb-postgres-connect/SKILL.md`, not a runtime Python change.

## Open Questions

- None.

## Requirements (evolving)

- Correct the documented skill install command to use the right repository subpath.
- Fix the reported connect YAML syntax problem in `skills/agent-kb-postgres-connect/SKILL.md` so GitHub can parse the frontmatter.
- Apply the install-command fix everywhere shipped docs currently document `npx skills add`, not just in one location.
- Update any tests that assert the old install command or old connect wording if needed.

## Acceptance Criteria (evolving)

- [ ] Docs show the correct `npx skills add .../skills --skill ...` command for the shipped skills.
- [ ] The reported connect syntax issue is reproduced or precisely identified, then fixed.
- [ ] Relevant tests pass after the change.

## Definition of Done (team quality bar)

- Tests added/updated where doc or script contracts are asserted
- Lint / typecheck / CI green where applicable
- Docs/notes updated if behavior changes
- Rollout/rollback considered if risky

## Out of Scope (explicit)

- Broad doc restructuring unrelated to install commands or the connect syntax issue
- Behavior changes outside the connect/install-command scope

## Technical Notes

- Files already inspected: `README.md`, `skills/agent-kb-postgres-connect/SKILL.md`, `tests/test_postgres_connect_tooling.py`, `tests/test_postgres_admin_tooling.py`.
