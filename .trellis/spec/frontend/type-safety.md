# Type Safety

> Current frontend type-safety status.

---

## Overview

No frontend TypeScript code exists yet, so there is no frontend type-safety convention to enforce.

The only active typed code in the repo today is Python with basic annotations, for example:

- `scripts/_postgres_admin_common.py`
- `scripts/create_principal.py`
- `scripts/manage_board_moderator.py`

This file should stay explicit about that absence instead of guessing a future TypeScript stack.

---

## Type Organization

Not defined for frontend code yet.

---

## Validation

No frontend runtime validation library is present in the repo.

Current validation lives in:

- Python CLI argument parsing via `argparse`
- Python checks that raise `SystemExit`
- PostgreSQL constraints, enums, helper functions, and RLS policies

---

## Common Patterns

No frontend type patterns exist yet.

---

## Forbidden Patterns

- Do not document `TypeScript`, `Zod`, or other frontend validation/type tools as established conventions until they are actually added.
- Do not cite example type files that do not exist in the repository.
