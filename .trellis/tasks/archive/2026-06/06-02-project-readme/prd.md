# brainstorm: project readme

## Goal

Write a project README that explains what this repository is, what has already been built, and how someone should get started using or extending it.

## What I already know

* The repo contains a PostgreSQL-backed agent knowledge base skeleton.
* There is a distributable skill at `skills/agent-kb-postgres-connect/SKILL.md`.
* There is a local Docker Compose setup and bootstrap SQL under `docker-compose.yaml` and `postgres/init/001-agent-knowledge-base.sql`.
* The repo also contains Trellis workflow/configuration files for multi-agent task execution.
* The README should serve both contributors and end users.
* The README should introduce the basic product capabilities.
* The README should explain how to use the project-distributed skill.
* The README should explain how to host/deploy the system.
* Hosting documentation should focus only on the current real self-hosting path.
* README should explain how to add accounts and manage account permissions.
* A dedicated admin-oriented skill plus helper scripts may be useful for account and permission operations.
* Here, "admin" means database-management operations performed by privileged users, not general application usage.
* This task should stop at README/documentation scope; admin skill and Python scripts should move to a follow-up task.
* The account/permission management section should use a balanced style: operational explanation plus a small number of key executable commands.
* Existing project skill layout is `skills/<skill-name>/SKILL.md`.
* The existing skill uses YAML frontmatter with `name` and `description`, then markdown sections for scope, inputs, commands, verification, and notes.
* This repo currently has one concrete example skill: `skills/agent-kb-postgres-connect/SKILL.md`.

## Assumptions (temporary)

* The README should open with a short product overview, then spend most of its depth on developer/contributor guidance.
* The README should likely include local setup, key files, current project status, skill usage, and hosting guidance.
* The hosting section should document the existing Docker Compose + PostgreSQL bootstrap path only.
* Account and permission management in this task should be documented as the current manual workflow.

## Open Questions

* None currently blocking.

## Requirements (evolving)

* README should describe the repository clearly.
* README should work for both contributors and end users.
* README should explain the system's basic functions.
* README should explain how to use the distributed skill under `skills/`.
* README should explain how to host the system.
* Hosting docs should cover only the currently supported self-hosting path.
* README should explain how to add accounts and manage role/moderator permissions.
* README should explain the project's skill structure and how to add/install/use the distributed skills at a practical level.
* For this task, document the current manual admin workflow instead of implementing the admin skill/scripts.
* The admin-management section should include a few core executable commands rather than exhaustive command coverage.
* README should note that a future admin skill and Python helper scripts are planned for privileged database management operations.

## Acceptance Criteria (evolving)

* [ ] README communicates the repo purpose and current state.
* [ ] README has a clear top-level explanation usable by non-contributors.
* [ ] README includes basic usage guidance for the distributed skill.
* [ ] README includes a hosting section aligned with the repo's real current setup.
* [ ] README documents the current account creation and permission-management workflow.
* [ ] Admin-only operations are documented through the current manual workflow, with a clear note about the planned follow-up admin skill/scripts.
* [ ] If admin scripting is too large for this task, the README clearly documents the current manual path and the scripting work is split into a follow-up task.
* [ ] README's management section is practical without becoming a full operations manual.

## Definition of Done (team quality bar)

* Tests added/updated if needed
* Docs reflect current behavior and structure

## Out of Scope (explicit)

* Implementing new product features
* Changing runtime behavior beyond documentation support
* General end-user posting or browsing workflows beyond brief README explanation
* Implementing the future admin skill and Python helper scripts

## Technical Notes

* Relevant current files: `docker-compose.yaml`, `postgres/init/001-agent-knowledge-base.sql`, `skills/agent-kb-postgres-connect/SKILL.md`, `tests/test_agent_kb_postgres_skeleton.py`
* Existing skill pattern observed:
  * path format: `skills/<skill-name>/SKILL.md`
  * YAML frontmatter: `name`, `description`
  * body sections: scope, required inputs, commands, verification, notes
* New requirement from user: admin skill should cover every operation that is not meant for a normal user, while remaining concise.
* New requirement from user: admin operations should be wrapped with Python scripts where practical.
* User chose to defer admin skill/script implementation to a follow-up task.
