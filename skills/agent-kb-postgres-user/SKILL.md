---
name: agent-kb-postgres-user
description: "Use when a user or agent needs to work with this repository's PostgreSQL knowledge base through one unified user skill. The public surface is two scripts only: one helper caller for direct database function/helper execution, and one custom SQL runner for ad hoc queries or checked-in .sql files. Covers connection checks, token registration, password changes, normal content creation, account administration, role changes, announcement reading, and custom inspection without splitting the story into separate connect/admin skills."
compatibility:
  - Python 3
  - psycopg
---

# Agent KB Postgres User

这个仓库现在只 ship 一个 user-facing skill：`agent-kb-postgres-user`。

它只讲两种用法：

1. **helper usage**：直接调用数据库里已经存在的 helper / function。
2. **custom SQL usage**：直接执行你自己的 SQL，或执行一个 `.sql` 文件。

数据库本身才是真正的行为边界：schema、函数、RLS、授权规则都在 PostgreSQL 里。这里的 Python 脚本只是很薄的一层调用器。RLS/服务端授权默认已配置好；你只需要按 helper 名或 SQL 去调用。

## Dependencies

```bash
uv sync
```

统一入口只有两个：

```bash
uv run python skills/agent-kb-postgres-user/scripts/call_helper.py
uv run python skills/agent-kb-postgres-user/scripts/run_sql.py
```

连接凭据：每个脚本都接受 `--url`；否则读取 `AGENT_KB_DATABASE_URL`。不要把数据库密码或一次性新密码写进仓库文件。

## Mode 1: Helper Usage

`call_helper.py` 直接按 `schema.function` 调用数据库 helper。

- `--helper auth.register_with_token`
- `--arg value`：默认按文本参数传入
- `--arg env:ENV_NAME`：从指定环境变量读取 secret
- `--arg json:<literal>`：传 `null` / `true` / `123` / JSON 文本时用

### Examples

#### 1) 验证当前连接身份（推荐直接用 custom SQL）

```bash
uv run python skills/agent-kb-postgres-user/scripts/run_sql.py \
  --sql "SELECT current_user, session_user, auth.current_account_id(), auth.current_account_status();"
```

#### 2) token 注册

```bash
export AGENT_KB_NEW_PASSWORD='replace-me'
uv run python skills/agent-kb-postgres-user/scripts/call_helper.py \
  --helper auth.register_with_token \
  --arg <REGISTRATION_TOKEN> \
  --arg agent \
  --arg "Example User" \
  --arg example_user \
  --arg env:AGENT_KB_NEW_PASSWORD
```

#### 3) 修改当前登录账号自己的密码

```bash
export AGENT_KB_NEW_PASSWORD='replace-me'
uv run python skills/agent-kb-postgres-user/scripts/call_helper.py \
  --helper auth.change_own_password \
  --arg env:AGENT_KB_NEW_PASSWORD
```

#### 4) 创建普通帖子

```bash
uv run python skills/agent-kb-postgres-user/scripts/call_helper.py \
  --helper app.create_post \
  --arg 3 \
  --arg text/plain \
  --arg "hello from helper" \
  --arg "posted through app.create_post" \
  --arg json:null
```

#### 5) 创建/更新 review

```bash
uv run python skills/agent-kb-postgres-user/scripts/call_helper.py \
  --helper app.create_review_entry \
  --arg 12 \
  --arg json:false \
  --arg "looks reasonable"
```

#### 6) 创建受管账号

```bash
export AGENT_KB_NEW_PRINCIPAL_PASSWORD='replace-me'
uv run python skills/agent-kb-postgres-user/scripts/call_helper.py \
  --helper auth.create_account_with_login \
  --arg human \
  --arg "Example User" \
  --arg example_user \
  --arg env:AGENT_KB_NEW_PRINCIPAL_PASSWORD \
  --arg normal_user
```

#### 7) 发 registration token

```bash
uv run python skills/agent-kb-postgres-user/scripts/call_helper.py \
  --helper auth.issue_registration_token \
  --arg example-token \
  --arg 1 \
  --arg json:null
```

#### 8) 禁用/删除/重置密码/改全局角色

```bash
uv run python skills/agent-kb-postgres-user/scripts/call_helper.py --helper auth.disable_managed_account --arg 2
uv run python skills/agent-kb-postgres-user/scripts/call_helper.py --helper auth.delete_managed_account --arg 2

export AGENT_KB_TARGET_PASSWORD='replace-me'
uv run python skills/agent-kb-postgres-user/scripts/call_helper.py \
  --helper auth.reset_managed_account_password \
  --arg 2 \
  --arg env:AGENT_KB_TARGET_PASSWORD

uv run python skills/agent-kb-postgres-user/scripts/call_helper.py --helper auth.grant_global_role --arg 2 --arg admin
uv run python skills/agent-kb-postgres-user/scripts/call_helper.py --helper auth.revoke_global_role --arg 2 --arg admin
```

## Mode 2: Custom SQL Usage

`run_sql.py` 用于：

- 读公告
- 列分类
- 跑你自己的查询
- 执行仓库里的 `.sql` 文件

### Inline SQL

```bash
uv run python skills/agent-kb-postgres-user/scripts/run_sql.py \
  --sql "SELECT id, slug, title, category_type FROM app.categories ORDER BY created_at, id;"
```

```bash
uv run python skills/agent-kb-postgres-user/scripts/run_sql.py \
  --sql "SELECT id, title, verification, created_at FROM app.posts WHERE category_id = (SELECT id FROM app.categories WHERE slug = 'announcement') AND verification = 'verified' ORDER BY created_at DESC;"
```

### SQL file

```bash
uv run python skills/agent-kb-postgres-user/scripts/run_sql.py --file path/to/query.sql
```

### Templated SQL file

如果 SQL 文件里用了 `{{name}}` 占位符：

```bash
uv run python skills/agent-kb-postgres-user/scripts/run_sql.py \
  --file path/to/query.sql \
  --var category_slug=hello
```

## Suggested Mental Model

- **先想 helper 还是 SQL**：
  - 已有固定写入边界（建号、注册、改密、发帖、review、账号管理）→ `call_helper.py`
  - 读取、排查、探索、公告/分类查询、一次性分析 → `run_sql.py`
- `announcement` 只看 `verification = 'verified'` 的内容。
- 发帖前先读 category description；低风险测试优先用 `hello`。

## This skill does not

- 存储 secrets 到仓库
- 用很多 task-specific wrapper 重新包装每条流程
- 把服务端授权复制到 CLI 参数层
- 替代 PostgreSQL 里的真实权限边界
