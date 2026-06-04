# Add psql examples to skill docs alongside Python

## Goal

在 Connect 和 Admin skill 文档中简要提示用户也可以用 `psql` 直接连接 PostgreSQL 执行 SQL，不局限于 Python 脚本。

## Requirements

- Connect SKILL 的 "Writing SQL Directly" 小节前加一句：可以用 `psql "$AGENT_KB_DATABASE_URL"` 直连
- Admin SKILL 的依赖/连接小节加一句：也可以用 `psql "$AGENT_KB_DATABASE_URL"` 执行 SQL
- 注明 `register_with_token()` 现在 psql 也可调用：`SELECT * FROM auth.register_with_token('token', 'agent', 'Name', 'login', 'pass');`

## Acceptance Criteria

- [ ] Connect SKILL 有 psql 连接提示
- [ ] Admin SKILL 有 psql 连接提示
- [ ] register_with_token psql 示例存在

## Out of Scope

- 为每个 Python 脚本都加 psql 等价命令
- 新增脚本文件
