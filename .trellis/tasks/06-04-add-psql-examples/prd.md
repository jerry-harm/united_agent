# Add psql examples to skill docs alongside Python

## Goal

在 skill 文档中为每个 Python 示例补充等价的 `psql` 命令，让用户既能用 Python 脚本也能直接用 psql 操作数据库。

## What I already know

- 当前 Connect SKILL.md 和 Admin SKILL.md 主要展示 Python 脚本示例
- Connect SKILL 已有 "Writing SQL Directly" 小节（lines 165-191），但只有少量 SQL 片段，没有完整的 psql 连接方式
- `register_with_token.py` 在客户端做 SHA-256 哈希，纯 psql 无法等价替代

## Assumptions (temporary)

- psql 示例以 `PGPASSWORD` 或 `pgpass` 方式提供凭据
- 每个 Python 入口对应一个 psql 等价命令

## Open Questions

* psql 示例放在哪里：嵌入在现有 Python 示例下方，还是集中到一个 "psql 等价命令" 小节？

## Requirements (evolving)

* 在 Connect SKILL 中为常用操作添加 psql 示例
* 在 Admin SKILL 中为特权操作添加 psql 示例
* 说明哪些操作必须用 Python（如 register_with_token）
* psql 连接凭据说明

## Out of Scope (explicit)

* 新建 psql 脚本文件
* 改变现有 Python 脚本

## Technical Notes

* 受影响的文件：`skills/agent-kb-postgres-connect/SKILL.md`, `skills/agent-kb-postgres-admin/SKILL.md`, `README.md`, `docs/developer-guide.md`
