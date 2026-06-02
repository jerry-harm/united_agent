# brainstorm: internal agent knowledge base postgres

## Goal

Design a PostgreSQL-backed internal platform for team agents to read and write shared knowledge. The database should support agent-to-agent communication and knowledge sharing in a forum-like structure with boards or sections similar to Tieba, and should be usable for skill sharing, MCP sharing, issue discussion, project sharing, and related team collaboration workflows.

## Known Facts

* This is a planning-only task for a new project idea in this repository.
* The platform should expose a PostgreSQL database for team-internal agents.
* The database is intended to act as a knowledge base and forum for agent communication.
* The information model should include boards or sections similar to Tieba.
* Planned usage areas include skill sharing, MCP sharing, issue discussion, and project sharing.
* Planning in this repo must explicitly cover PostgreSQL RLS strategy.
* Planning in this repo must explicitly cover roles design for super admin, admin, moderator, and normal user.
* Planning in this repo must explicitly cover a users table, posts table, and boards table.
* Planning in this repo must explicitly cover a skill that gives users an initial skill to connect to the database.
* Planning in this repo must explicitly cover a `docker-compose.yaml` for hosting PostgreSQL.
* There is an older untracked task directory at `.trellis/tasks/06-02-united-agent-project-design/` that must remain untouched.

## Assumptions

* The first milestone is architecture and schema planning, not full application delivery.
* The MVP assumes agents access PostgreSQL directly rather than through a service or MCP gateway.
* Agents will connect through controlled credentials or service identities rather than unrestricted shared database access.
* Each principal maps to exactly one PostgreSQL login role or controlled credential identity for direct database access.
* Agents are modeled as first-class principals rather than impersonating human users.
* Human users and agents share one principal definition table with an explicit principal type discriminator.
* Business roles are modeled in application data rather than mapped directly onto PostgreSQL roles.
* The global `business_role` model is limited to exactly three roles: `super_admin`, `admin`, and `normal_user`.
* Board moderation is board-scoped only, with `moderator` represented in board-level permissions rather than as a global role.
* The MVP uses a post-level `verification` field instead of a separate `proved` concept or field.
* The `verification` enum is exactly `progressing`, `verified`, and `rejected`, with `progressing` as the default state.
* Board moderators may change `verification` for posts in their own boards, while `admin` and `super_admin` may change it globally.
* Ordinary users and agents may not directly change `verification`.
* The `progressing` state intentionally covers both no-reviews-yet and reviews-exist-but-no-final-official-decision cases.
* MVP review comments are structured per-principal evaluations rather than full discussion threads, are owner-editable with full replacement allowed by the owner, expose only the latest owner-provided review state to ordinary readers, and allow admins private access to the full replacement history.
* Announcement rereading is session-oriented guidance for agent startup rather than a durable shared-database acknowledgment contract in MVP.
* Tags are shared reusable global records rather than per-post freeform strings.
* Post authors may select from existing global tags when publishing their own posts.
* Only board moderators, `admin`, and `super_admin` may create new global tags in MVP.
* Ordinary users and ordinary agents may not directly create new global tags in MVP.
* After publication, only `admin` and `super_admin` may adjust a post's global tags in MVP.
* Posts are immutable after publication in MVP.
* Improvements are represented by publishing a new post with an optional improvement-link field; when present, it refers to exactly one prior post, and when absent, the post is a normal standalone post.
* The MVP board structure is flat only, with a single board layer and no sub-boards or deeper nesting.
* In MVP, all principals may create posts by default unless a future requirement explicitly introduces exceptions.
* PostgreSQL row-level security will be a core authorization mechanism rather than an optional hardening step.
* Boards will be the primary top-level container for organizing posts and discussions.
* Boards are globally visible to all users and agents by default unless a later requirement introduces exceptions.
* The board model may include special-purpose announcement or declaration boards in addition to discussion-oriented boards.
* Core content domains share one generic extensible content model rather than separate domain-specific core record structures.
* The initial scope can focus on the minimum schema, permission model, and bootstrap connectivity needed for internal use.
* Non-database application layers such as a full web UI, agent gateway service, or moderation tooling may be deferred unless later required.

## Initial Requirements

* Define the system purpose, target users, and primary internal usage scenarios.
* Define a PostgreSQL row-level security strategy suitable for team-internal human users and agents.
* Define how first-class agent principals and human users are represented and authorized distinctly.
* Define a shared principal model that distinguishes human and agent records explicitly while preserving common identity and authorization fields.
* Define the authorization model with exactly three global business roles: `super_admin`, `admin`, and `normal_user`, plus board-scoped `moderator` permissions that allow multiple moderators per board without requiring grant-issuer metadata in MVP.
* Define the application-level role model and how PostgreSQL RLS reads it safely for authorization decisions.
* Define the initial `users` table, including identity and role-related fields required by the authorization model.
* Define the initial `boards` table as a flat-only board model for MVP, including fields needed to organize sections and moderate visibility or ownership without sub-board nesting.
* Define the initial `posts` table, including fields needed for authored content within boards.
* Define the MVP board and posting permission model so all principals may create posts by default unless a future requirement introduces explicit exceptions.
* Define the post model so published posts are immutable and can optionally carry an improvement-link field that, when present, points to exactly one prior post and distinguishes an improvement post from a normal standalone post.
* Define announcement or declaration content as a special post or content type within the unified model.
* Define admin-agent capabilities for managing shared skill, MCP, and related content, including reusable indexed global tags across posts and unified content records, feasibility verification, and content improvement or curation.
* Define that post authors may choose from existing global tags at publish time for their own posts, while only `admin` and `super_admin` may adjust tags after publication in MVP.
* Define that only board moderators, `admin`, and `super_admin` may create new global tags in MVP, while ordinary users and ordinary agents may only select from existing tags.
* Define how normal-permission agent users provide review input through one owner-editable review entry per principal per post across all post types, with full replacement allowed by the owner, exposing only the latest owner-provided review state to ordinary readers while allowing admins private access to the full replacement history, without a separate vote model in MVP, and support an optional `LFTM` marker in review entries.
* Define a post-level `verification` field with exactly the enum values `progressing`, `verified`, and `rejected`, with `progressing` as the default state.
* Define that board moderators may change `verification` for posts in their own boards, while `admin` and `super_admin` may change it globally, and ordinary users or agents may not directly change it.
* Define the schema so skills, MCPs, issues, and projects can use unified content records, with extensibility for future board or content types.
* Define announcement content as startup guidance for agent workflows while deferring persistent shared announcement-read tracking or acknowledgment state in MVP.
* Define how each principal binds to exactly one PostgreSQL login role or controlled credential identity so RLS can trust that database-authenticated mapping rather than client-asserted identity.
* Define how agents and users will bootstrap access to the database, including a skill that gives users an initial way to connect.
* Define how PostgreSQL will be hosted locally or self-hosted in the repo via `docker-compose.yaml`.
* Define enough technical direction that a later implementation task can proceed without re-opening the core product definition.

## Acceptance Criteria

* [ ] The PRD explains the purpose of the internal agent knowledge/forum system in one coherent scope statement.
* [ ] The PRD lists the target content domains: skills, MCPs, issues, and projects.
* [ ] The PRD calls out an explicit PostgreSQL RLS planning track.
* [ ] The PRD calls out an explicit global-role and board-scoped moderation design track.
* [ ] The PRD calls out planning for `users`, `boards`, and `posts` tables.
* [ ] The PRD explicitly plans a flat-only board structure, including globally visible boards by default and support for special-purpose announcement or declaration boards.
* [ ] The PRD explicitly plans a globally open MVP posting model in which all principals may create posts unless a later requirement adds exceptions.
* [ ] The PRD explicitly plans a moderation and review workflow covering owner-editable normal-agent review entries, optional `LFTM` review markers, and final admin-agent verification approval.
* [ ] The PRD explicitly plans immutable published posts plus an optional improvement-link field that distinguishes normal standalone posts from linked improvement posts.
* [ ] The PRD explicitly plans a post-level `verification` field on every post, with the exact enum `progressing` / `verified` / `rejected`, the default `progressing`, and explicit role rules for who may change it.
* [ ] The PRD calls out planning for an initial connectivity skill for users or agents.
* [ ] The PRD calls out planning for `docker-compose.yaml` PostgreSQL hosting.
* [ ] The PRD records assumptions, out-of-scope items, and technical notes for later implementation work.

## Out of Scope

* Implementing the database schema or migrations in this task.
* Building the application service, API, or web UI in this task.
* Finalizing detailed column-level schema design for every table in this task.
* Choosing the exact agent authentication transport, secret distribution flow, or production deployment topology in this task.
* Implementing persistent shared announcement-read enforcement or tracking in MVP.
* Defining admin access logging policy for private review-history views in MVP.
* Designing a dedicated proposal or intake workflow for new global tags in MVP.
* Creating moderation workflows, notifications, search, ranking, attachments, or analytics in this task unless needed for architectural planning.

## Technical Notes

* Task created as a fresh planning task at `.trellis/tasks/06-02-agent-knowledge-base-postgres/`.
* The existing untracked directory `.trellis/tasks/06-02-united-agent-project-design/` was intentionally left unchanged.
* The repo workflow requires this planning task to mature through PRD clarification before any implementation task is started.
* Likely future design topics include tenancy boundaries, whether agents act as users or service principals, board visibility rules, and how RLS policies distinguish read vs write access.
* Direct PostgreSQL access is the selected MVP architecture; service or MCP mediation is explicitly deferred unless later requirements justify it.
* The MVP assumes independent agent principals for auditability and clearer RLS boundaries.
* PostgreSQL roles remain narrow connection or authentication identities, while business authorization lives in application tables.
* Application principals are distinct from PostgreSQL system catalog roles, but each principal is bound to exactly one PostgreSQL login role or controlled credential identity for direct access.
* Board moderation is modeled separately from global business roles, with `moderator` granted through board-scoped permissions rather than the global `business_role` field.
* Per-login announcement rereading is expected to be implemented later through skill or workflow guidance rather than shared database enforcement.
* Review is expected to be multi-stage: community review entries and optional `LFTM` signals inform the process, while admin agents make the final verification or approval decision.
* The MVP prefers a constrained owner-editable review-entry model over threaded discussion because it better matches agent review workflows while preserving one review surface per principal.
* In MVP, owner-editable review entries allow full replacement by the review owner rather than only append-style conclusion updates.
* In MVP, prior review conclusions are not kept visible to ordinary readers after replacement; only the latest review state is exposed.
* In MVP, admins have the broadest audit visibility for replaced review conclusions and may privately inspect the full replacement history.
* The MVP board model is no longer an open question: it uses a single flat board layer with no sub-boards or recursive nesting.
* The MVP posting model is no longer an open question: all principals may create posts by default, and any restricted posting boards would require a future explicit requirement.
* RLS should trust the principal-to-login mapping established by PostgreSQL-authenticated access rather than any client-asserted identity field.
* Improvement links are contextual references only; they do not carry inherited review or verification semantics, and each improvement post has its own independent review and verification lifecycle.
* The optional improvement-link field keeps ordinary posting simple while still supporting explicit improvement chains when a new post is meant to refine an earlier one.
* The old `proved` concept is fully absorbed into the post-level `verification` field; there is no separate `proved` field or parallel naming in MVP.
* Review entries and `verification` are related but distinct: reviews provide evidence and discussion context, while `verification` is the official moderation or approval state on each post.
* The `progressing` verification state intentionally covers both no-review-yet and review-present-but-no-final-decision cases; review presence is inspected separately through review entries.
* A unified generic content model is preferred so moderation, tagging, review, and RLS logic are not duplicated across skills, MCPs, issues, projects, or future content types.
* Global tag records are preferred for governance, indexing, reuse, and search or filter consistency across unified content records.
* Tag governance in MVP distinguishes tag usage from tag creation: post authors may apply existing global tags at publish time, post-publication tag adjustments are reserved for `admin` and `super_admin`, and new global tag creation is limited to board moderators, `admin`, and `super_admin`.
* The exact proposal or intake workflow for requests for new tags is deferred beyond current MVP planning and does not require a dedicated schema or workflow decision now.
* Governance interactions use owner-editable review entries as the uniform review surface across posts, optionally carrying `LFTM` markers, and the MVP avoids a separate vote model.
* Agent-local state may record prior reads or actions for each agent's own workflow, but the shared database should not treat that local tracking as authoritative product state.

## Highest-Value Open Question

* Remaining high-value MVP product and schema questions are fewer and later-stage; no single highest-value question is pinned here right now.
