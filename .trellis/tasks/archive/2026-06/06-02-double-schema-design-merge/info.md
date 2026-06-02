## Two-task implementation split

This design task concludes with a deliberate two-step implementation plan.

### Task 1

Path: `.trellis/tasks/06-02-dual-schema-permission-model-refactor/`

Scope:
- introduce the `auth` schema boundary
- replace `app.principals` with `auth.accounts`
- move authorization relations into `auth`
- rewrite helper functions and RLS around grant tables and `auth.can_write()`
- include `FORCE RLS`, `public` privilege tightening, and helper `search_path` tightening

### Task 2

Path: `.trellis/tasks/06-02-management-entrypoints-docs-migration/`

Scope:
- migrate admin/helper entrypoints to the new schema layout
- update docs/spec/README terminology from principals/business-role-column assumptions to accounts/grants
- refresh regression and verification coverage

### Intent

Keep schema and permission semantics in Task 1, then move operational tooling and documentation cleanup into Task 2. No data-migration compatibility layer is planned at this stage; destructive bootstrap reset remains acceptable for MVP development.
