# Update README npx skills install wording

## Goal

Replace the current README `npx skills` wording with two concrete `npx skills add` commands (one per shipped skill) pointed at the public `jerry-harm/united_agent` repository, and drop the local-path / "直接读 SKILL.md" fallback so the README is a clean install-then-quickstart entry point.

## What I already know

* The repo currently ships two skills under `skills/agent-kb-postgres-connect` and `skills/agent-kb-postgres-admin`; both exist as subdirectories at the public `https://github.com/jerry-harm/united_agent` repository (verified via the GitHub contents API).
* `vercel-labs/skills` is the upstream `npx skills` tool, and its README documents the `npx skills add <owner>/<repo> --skill <name>` source format. The two-flag form (`--skill agent-kb-postgres-connect`, `--skill agent-kb-postgres-admin`) is the documented way to install specific skills from one repo.
* The current README `## 先装/导入仓库自带 skills` section names the two local skill directories and hedges with "不同宿主对 `npx skills` 的具体子命令可能叫 `install`、`import` 或 `add`"; we now have a verified `add` form, so that hedge is no longer needed.
* `tests/test_postgres_connect_tooling.py::test_readme_mentions_connect_skill_script_and_live_test` asserts the README contains the literal string `npx skills`; the new wording must keep that token.
* `tests/test_postgres_admin_tooling.py::test_readme_mentions_admin_skill_and_helper_scripts` exists in the same shape and similarly depends on the README's wording, so any admin-skill phrase changes must keep admin-related content present.
* The current README already keeps the two skill directory list (just the paths) so the `skills/agent-kb-postgres-connect/SKILL.md` and `skills/agent-kb-postgres-admin/SKILL.md` literals still appear; only the install/import block needs surgery.

## Assumptions (temporary)

* The two `npx skills add ... --skill <name>` commands are the form the user wants; verified via user response "首先这个命令安装的是skill而不是整个项目,所以要是两个安装skill的命令而不是一个安装我整个项目的命令."
* The README should drop the local path SKILL.md fallback per user response "只留 npx skills 命令".
* We do not need to bump or republish anything to npm / skills.sh; only the README text changes.

## Open Questions

* None — scope is constrained by the two confirmed user answers.

## Requirements (evolving)

* The README `## 先装/导入仓库自带 skills` section must show two concrete `npx skills add` commands, one per shipped skill, using the public `jerry-harm/united_agent` repository and the documented `--skill <name>` form.
* The README must no longer present the `./skills/agent-kb-postgres-connect` and `./skills/agent-kb-postgres-admin` directories as install/import sources, and must no longer offer the local SKILL.md fallback paragraph.
* The README must still keep the two skill directory list (or equivalent short description) so the rest of the document's `skills/agent-kb-postgres-connect/...` paths stay meaningful to readers.
* The literal token `npx skills` must still appear in the README so the existing static test in `tests/test_postgres_connect_tooling.py` keeps passing.
* The wording must not introduce any unverified CLI syntax (no invented subcommands, flags, or scoping rules); stick to the forms documented by `vercel-labs/skills`.

## Acceptance Criteria (evolving)

* [ ] README contains two `npx skills add jerry-harm/united_agent --skill agent-kb-postgres-connect` and `npx skills add jerry-harm/united_agent --skill agent-kb-postgres-admin` commands (exact `add` subcommand, exact `--skill` flag spelling).
* [ ] README no longer contains the `./skills/agent-kb-postgres-connect` or `./skills/agent-kb-postgres-admin` install/import block (the skill directory paths may still appear elsewhere in the doc).
* [ ] README no longer contains the "如果你的环境不走 `npx skills`" fallback sentence.
* [ ] README still contains the literal `npx skills` so `test_postgres_connect_tooling.py::test_readme_mentions_connect_skill_script_and_live_test` stays green.
* [ ] `python3 -m py_compile` and `uv run python -m unittest discover -s tests -v` both stay green.

## Definition of Done (team quality bar)

* README wording matches the verified upstream `vercel-labs/skills` syntax, no invented flags.
* Existing static README tests still pass without modification.
* Other skill/admin/docs that still mention the two skill paths keep working (the local script paths under `skills/.../scripts/...` are untouched).

## Technical Approach

* Edit `README.md`: rewrite the `## 先装/导入仓库自带 skills` block. Drop the local-path install/import list and the SKILL.md fallback paragraph. Replace them with two fenced `bash` blocks showing the two `npx skills add` commands, with a one-line preface that explains each command installs exactly one skill from the public repo.
* Leave the rest of the README (quickstart, "什么时候用哪个 skill", "继续阅读") untouched because it is downstream of the install path and still references the two skills correctly.

## Decision (ADR-lite)

**Context**: The README previously pointed users at `./skills/...` directories and a "可能叫 `install`/`import`/`add`" hedge, because we had not yet verified the upstream `vercel-labs/skills` CLI. The user now wants concrete, verified `npx skills add` commands and prefers dropping the local-path fallback.

**Decision**: Use the documented `npx skills add <owner>/<repo> --skill <name>` form, one command per shipped skill, and remove the local-path install/import paragraph from the README. The two `skills/agent-kb-postgres-*/SKILL.md` lines stay as descriptive bullets; only the install/import instructions change.

**Consequences**: The README is shorter and the install path is unambiguous. The user must run two `npx skills add` commands instead of one, but each command installs only the skill the user asked for, which is exactly what the user wants. No operational behavior changes inside the repo.

## Out of Scope (explicit)

* Publishing the skills to a registry or skills.sh.
* Bumping version metadata or release tags.
* Editing `docs/developer-guide.md` or `docs/design-philosophy.md` (the user only asked for the README).
* Editing the `SKILL.md` files themselves; only the README install wording changes.
* Adding or removing any skill under `skills/`.

## Technical Notes

* Verified CLI source formats from `vercel-labs/skills` README:
  * `npx skills add <owner>/<repo> --skill <name>` is the supported form for installing a single skill by name.
  * Source formats include `owner/repo`, full GitHub URLs, GitLab URLs, any git URL, and a local path — but we only need the GitHub shorthand for this task.
* Verified online repo structure: `https://github.com/jerry-harm/united_agent` exposes `skills/agent-kb-postgres-admin` and `skills/agent-kb-postgres-connect` at the repo root.
* Files inspected:
  * `README.md` (current install block)
  * `tests/test_postgres_connect_tooling.py` (asserts `npx skills` literal)
  * `tests/test_postgres_admin_tooling.py` (related admin-skill README assertions)
  * `https://raw.githubusercontent.com/vercel-labs/skills/main/README.md` (CLI syntax)
  * `https://api.github.com/repos/jerry-harm/united_agent/contents/skills` (online skills layout)
* Risks: if the user later renames either skill directory on the public repo, the documented `--skill` names will need to be updated alongside.
