# registration and registration application flow

## Goal

Add a project-native way to handle user onboarding beyond admin-only account creation, covering either direct self-registration, registration-application review, or both.

## What I already know

* This repository is PostgreSQL-first; the database schema and helper scripts are the primary product surface.
* Current documented account onboarding is admin-driven via `skills/agent-kb-postgres-admin/scripts/create_principal.py`.
* Current normal-user self-service flow only covers connecting, verifying identity, posting/reviewing, and changing the current account password.
* `create_principal.sql` currently creates a PostgreSQL login, inserts `auth.accounts`, and grants a global role in one privileged path.
* Current role policy is strict: `admin` may create only `normal_user`; `super_admin` may create `admin`; nobody creates `super_admin` through the helper.
* I have not found an existing `registration`, `signup`, `application`, or `pending account` model yet.

## Assumptions (temporary)

* "注册" may mean direct self-service account creation by an unauthenticated actor.
* "申请注册" may mean a request queue that an admin later approves or rejects.
* The desired solution should likely stay consistent with the current PostgreSQL-first + helper-script architecture rather than introducing a full web app by default.

## Open Questions

* None currently.

## Requirements (evolving)

* Support a new onboarding capability that is not limited to current admin-only account creation.
* Support an invite-like registration entrypoint that can be used anonymously.
* The anonymous entrypoint must be single-use and hard to guess.
* The selected MVP is direct registration: a valid one-time token immediately creates a `normal_user` account.
* The registration path must not expose a global public signup surface without a token.
* Token consumption must be atomic so concurrent reuse attempts cannot create two accounts.
* The new registration path must never create roles above `normal_user`.
* Only `admin` and `super_admin` may create registration tokens.
* A registration token may be configured with a maximum number of successful uses instead of being hardcoded to single-use only.
* When `max_uses > 1`, all registrants reuse the same token string until the quota is exhausted.
* Token expiration is optional: a token may be non-expiring, or may expire at an admin-specified timestamp.
* Rename the current review boolean concept from `LFTM` to `LGTM` across schema, views, scripts, docs, and tests.
* The default seeded announcement must explain what `LGTM` means and how to use it.
* The default seeded announcement must explain that `LGTM` is not the same as `verified`; `verified` is a higher standard of recognition.
* `conclusion` stays free text; before submitting, the author should ensure there are no obvious factual errors and the logic is basically coherent.
* Review entries remain updatable, and the latest conclusion is the effective one while prior values stay in `app.review_history`.
* The shipped skills and their bundled helper scripts/docs must be updated together with the database changes so registration and review terminology stay executable and documented.

## Technical Approach

### Approach A: registration application review flow (recommended)

* Add a new pending-request model, likely an `auth.registration_applications` table.
* Anonymous or low-trust actors submit an application containing the minimum onboarding fields.
* No PostgreSQL login role is created at submission time.
* Admin reviews the application, then approval triggers the existing account-creation path or a closely aligned variant of it.
* Rejection leaves an auditable record without creating a login.

### Approach B: direct self-registration

* Add a self-registration entrypoint that accepts signup fields and immediately creates a PostgreSQL login plus `auth.accounts` row.
* This requires a carefully scoped privileged helper, because an unauthenticated actor cannot safely run the current admin-only account-creation path directly.
* The flow should force new accounts into a constrained role such as `normal_user` only.
* Additional safeguards are needed for uniqueness, abuse control, and password handling because account creation happens before any human review.

### Approach C: hybrid

* Support both direct registration and application review.
* Usually implemented by making one the default and the other an alternate path.
* Highest flexibility, but also the largest scope because docs, policy, tests, and failure cases double.

### Approach D: single-use anonymous registration token

* Admin pre-creates a registration token similar to an invite code.
* The token identifies an anonymous registration slot with a configurable use quota.
* The submitter uses the token to create a constrained `normal_user` account directly.
* Token usage is consumed atomically and may not exceed the configured `max_uses`.
* The token must be unguessable; the system should not rely on exposing a real random table name as the primary security boundary.

### Selected direction

* Use a fixed token table plus a guarded registration helper, not random physical tables.
* A token holder may create up to the token's configured `max_uses` number of `normal_user` accounts.
* The helper creates the PostgreSQL login, creates `auth.accounts`, grants `normal_user`, and marks the token used in one transaction.
* Multi-use tokens are shared tokens, not parent tokens that fan out into per-use child tokens.
* Expiration is modeled as an optional `expires_at`; `NULL` means the token does not expire.
* `LFTM` terminology is renamed to `LGTM` in the same task because the seeded announcement must teach the new semantics.

## Decision (ADR-lite)

**Context**: The repository currently supports admin-created accounts and ordinary-user self-service password change, but no native self-signup or review queue.

**Decision**: Implement admin-created token-based direct registration for `normal_user` only, with configurable max-uses quotas, and rename `LFTM` to `LGTM` with updated seeded announcement guidance.

**Consequences**:

* Application-review aligns best with the current privilege model.
* Direct registration reduces friction but needs a new trust boundary for privileged account creation.
* Hybrid likely exceeds MVP scope unless both paths are explicitly required.
* Single-use anonymous token flow can reduce abuse without opening global public signup, but should be implemented as data rows plus one guarded function/script, not as physically random table names.
* The `LFTM` to `LGTM` rename is a cross-cutting terminology migration, not a wording-only patch.

## Acceptance Criteria (evolving)

* [ ] The supported onboarding flow is clearly defined.
* [ ] The actor boundaries and approval boundaries are clearly defined.
* [ ] A valid token can create up to its configured `max_uses` number of `normal_user` accounts.
* [ ] Reusing a token after its quota is exhausted fails without creating an extra account.
* [ ] The shipped default announcement teaches the `LGTM` vs `verified` distinction.
* [ ] Shipped skill flows and docs expose the new registration-token path and the `LGTM` terminology.

## Definition of Done (team quality bar)

* Tests added or updated where appropriate.
* Lint / typecheck / CI green.
* Docs updated if behavior changes.
* Rollback / safety considered if risky.

## Out of Scope (explicit)

* Any web UI, unless explicitly required.
* Any relaxation of current admin / super_admin policy outside the approved registration design.

## Technical Notes

* Relevant docs read: `README.md`, `docs/developer-guide.md`, `.trellis/spec/backend/index.md`.
* Relevant code read: `skills/agent-kb-postgres-admin/scripts/create_principal.py`, `skills/agent-kb-postgres-admin/scripts/sql/create_principal.sql`.
* Relevant tests read: `tests/test_connect_skill_live_flows.py`.
