# Compress connect & admin SKILL.md

## Goal

压缩 `agent-kb-postgres-connect/SKILL.md` 和 `agent-kb-postgres-admin/SKILL.md`，用尽可能简短的语言，减少冗余描述。

## Changes

### Connect SKILL.md

1. **Quickstart 删第 236 行重复** — `python3 verify_connection.py` 是重复的（前面 `uv run` 已经执行过）

2. **压缩 "When to Interact" 章节** — 每个 trigger 用最简一句话，SQL 保持注释精简，去掉"General rules"中与 board description 重复的规则

3. **压缩其他章节** — Announcement、Quickstart、Tooling 各处描述精简

### Admin SKILL.md

- 基本 OK（之前 review 确认），快速扫一遍有没有明显冗余

## Principles

- 触发时机描述 ≤ 1 行
- SQL 注释尽量短或去掉
- 不丢失关键信息（board slug、verification 规则、format 要求）
- 保持中文

## Out of Scope

- 不改 list_content.py
- 不改 init.sql
- 不做 eval/测试（纯压缩，无功能变化）
