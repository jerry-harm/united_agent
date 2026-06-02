# brainstorm: united agent project

## Goal

Design the first shippable version of `united_agent`: a project that gives one coherent product direction, one clear MVP boundary, and one implementation path that can be executed incrementally in this repo.

## What I already know

- The repository is newly initialized and currently contains Trellis workflow scaffolding plus `AGENTS.md`.
- There is no application code, README, package manifest, or existing runtime architecture yet.
- The repo is on branch `main` with a clean working tree and a single `init` commit.
- The project name suggests a "unified" or "united" agent concept, but the exact product target is still undefined.

## Assumptions (temporary)

- We are designing a new product from scratch rather than extending an existing service.
- The first step should be product definition and architecture, not implementation.
- The MVP should stay narrow enough to build in a few focused tasks after this design phase.

## Open Questions

- What exact product category should `united_agent` be?
- Who is the primary user of the first version?
- What core workflow must the MVP complete end-to-end?

## Product Direction Options

### 1. Multi-agent coding orchestrator

- Target user: Individual developers who want one tool to coordinate planning, implementation, verification, and handoff across multiple coding agents.
- Core workflow: The user defines a coding task, the system breaks it into agent jobs, dispatches implementation and review steps, then returns one merged result and status trail.
- Why it is a good MVP: It fits the current repo's Trellis-heavy workflow context and can start with a narrow developer-facing orchestration loop.
- Main risk: It may overlap too much with existing agent runners and feel like a thin wrapper without a sharper differentiator.

### 2. Team AI development workflow orchestrator

- Target user: Small engineering teams that need a shared AI-assisted workflow for planning, execution, review, and task tracking.
- Core workflow: A team creates scoped work items, routes them through a standardized AI workflow, tracks progress across contributors, and keeps specs, checks, and delivery artifacts aligned.
- Why it is a good MVP: It turns the repo's existing Trellis workflow ideas into the product itself and creates a clearer operational problem to solve than single-user agent dispatch alone.
- Main risk: Team workflow products can become broad quickly, so the first version must avoid trying to replace every project management or CI tool.

### 3. Unified model/tool gateway

- Target user: Developers or internal platform teams that want one interface for multiple LLM providers, tools, and execution environments.
- Core workflow: The user sends one request through a common gateway, the system selects or routes models and tools, and returns normalized outputs, logs, and controls.
- Why it is a good MVP: It has a simple platform story and could provide immediate value by reducing provider-specific integration work.
- Main risk: It is crowded, infrastructure-heavy, and may pull the project toward API plumbing instead of a distinctive workflow product.

## Current Recommendation

- Recommend option 2: it has the strongest alignment with the Trellis workflow assets already present in this repo.
- Recommend option 2: it gives `united_agent` a clearer product identity around team execution discipline, not just model routing or agent fan-out.

## Requirements (evolving)

- Define the primary user and their core job-to-be-done.
- Define the MVP scope and explicit out-of-scope items.
- Define a concrete technical architecture suitable for this repo.
- Break the post-design implementation into small Trellis tasks.

## Acceptance Criteria (evolving)

- [ ] Product direction is concrete enough to explain in 2-3 sentences.
- [ ] Primary user and primary workflow are explicit.
- [ ] MVP scope and non-goals are written down.
- [ ] Initial architecture and repo layout are chosen.
- [ ] Next implementation tasks are identified.

## Definition of Done (team quality bar)

- Design decisions are documented in `prd.md`.
- Architecture is specific enough to start implementation without guessing.
- MVP scope is narrow and testable.
- Follow-up tasks can be created directly from this document.

## Out of Scope (explicit)

- Building production code before product direction is fixed.
- Premature support for every possible agent provider or workflow.
- Infrastructure decisions that depend on an undefined MVP.

## Technical Notes

- Existing repo file inspected: `AGENTS.md`
- Trellis workflow inspected: `.trellis/workflow.md`
- Active design task: `.trellis/tasks/06-02-united-agent-project-design/`
