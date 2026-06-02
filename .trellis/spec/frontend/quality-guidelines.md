# Quality Guidelines

> Current quality guidance for frontend work in this repo.

---

## Overview

There is no frontend codebase yet, so there is no active frontend lint/test stack to enforce.

The useful current rule is process-oriented: the first task that adds real frontend code must also update these frontend spec files to match the chosen stack.

---

## Forbidden Patterns

- Pretending a frontend implementation already exists.
- Adding frontend spec text copied from generic templates without repo examples.
- Describing API/UI integration paths that are not shipped yet.

---

## Required Patterns

When the first frontend code is introduced, the same task should:

- update `README.md` if project surface area changes
- replace these placeholder-absence notes with real conventions
- add real file-path examples to every frontend spec file it establishes
- add the actual verification commands for the chosen stack

---

## Testing Requirements

No frontend-specific test command exists today.

Do not claim frontend linting, accessibility automation, or component tests are required until those tools exist in the repo.

---

## Code Review Checklist

- Does the change describe only frontend code that actually exists?
- If a frontend stack is introduced, were the corresponding spec files updated immediately?
- Were verification commands added to the repo, not just mentioned in docs?
