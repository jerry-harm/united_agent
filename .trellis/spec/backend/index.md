# Backend Development Guidelines

> Best practices for backend development in this project.

---

## Overview

This directory captures the backend conventions that exist in this repository today.

---

## Guidelines Index

| Guide | Description | Status |
|-------|-------------|--------|
| [Directory Structure](./directory-structure.md) | Module organization and file layout | In use |
| [Database Guidelines](./database-guidelines.md) | PostgreSQL schema, RLS, bootstrap, and migration conventions | In use |
| [Error Handling](./error-handling.md) | Error types, handling strategies | In use |
| [Quality Guidelines](./quality-guidelines.md) | Code standards, forbidden patterns | In use |
| [Logging Guidelines](./logging-guidelines.md) | Structured logging, log levels | In use |

---

## How to Use These Guidelines

When writing or reviewing backend changes:

1. Start with the guideline file that matches the area you are touching
2. Follow the real file-path examples cited there
3. Preserve listed forbidden patterns unless the codebase changes and the spec is updated in the same task
4. Update these docs when backend reality changes

The goal is to help AI assistants and new team members understand how YOUR project works.

---

**Language**: All documentation should be written in **English**.
