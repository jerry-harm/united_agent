# State Management

> Current frontend state-management reality.

---

## Overview

No frontend state-management solution exists yet because no frontend implementation exists.

The current project state is:

- persistent data lives in PostgreSQL
- authorization state is enforced in SQL/RLS helpers
- admin workflows run through Python scripts and `psql`-style operator flows
- there is no browser local state, global state store, or server-state cache layer in the repo

---

## State Categories

Frontend state categories are not defined yet.

Backend-side state that already exists and should not be misdescribed as frontend state includes:

- account identity in `auth.accounts`
- global role grants in `auth.principal_global_roles`
- public profile state in `app.profiles`
- content and review state in `app.*` tables

---

## When to Use Global State

No frontend global-state rule exists yet.

Do not introduce Redux/Zustand/Context conventions into specs until the repo actually adopts one.

---

## Server State

There is no frontend server-state cache contract yet.

If a future UI is added, document the real fetching/caching tool and invalidation model here in the same task.

---

## Common Mistakes

- Treating database authorization state as if it were already mirrored in a client store.
- Picking a frontend state library in docs before any code or tooling chooses one.
