# refactor-guest-login-and-rename-db-url-env

## Goal

重构 `auth.accounts` 表结构：将公开资料字段（`principal_type`, `display_name`）移到新建的 `app.profiles` 表，收紧 `auth.accounts` 的可见性。新增 `bio` 字段。修正 `register_with_token` 注释与代码不一致问题。保留 `AGENT_KB_DATABASE_URL` 不变，保留 guest 硬编码密码不变。

## Requirements

### 1. 新建 `app.profiles` 表
- 字段：`id bigserial PK`, `account_id FK→auth.accounts(id)`, `principal_type`, `display_name`, `bio text`, `created_at`, `updated_at`
- `account_id` 为 UNIQUE，一对一关系
- 默认 `bio` 为空字符串

### 2. 重构 `auth.accounts` 表
- **移除** `principal_type` 和 `display_name` 列
- 保留：`id`, `pg_login_role`, `account_status`, `created_at`, `updated_at`
- 收紧 SELECT RLS：普通用户只能看自己的行，admin 看全部

### 3. `app.profiles` RLS 策略
- SELECT：所有人可读（包括 guest）
- INSERT：仅 admin（注册时由 `register_with_token` SECURITY DEFINER 插入）
- UPDATE：自己的 profile（`account_id = auth.current_account_id()`）
- DELETE：禁止（profile 跟随 account 生命周期）

### 4. `register_with_token` 修正
- 移除 line 1078 注释 "允许未映射到 auth.accounts 的低权限 PostgreSQL login 调用"
- 明确注释：仅 guest 可调用
- `principal_type` 参数可随意指定，默认 `agent`
- 注册时同时创建 `auth.accounts` 行和 `app.profiles` 行

### 5. 更新所有引用
- SQL 函数中引用 `a.display_name` / `a.principal_type` 的 → JOIN `app.profiles`
- Python 脚本中引用 `display_name` / `principal_type` 的 → 更新 SQL 或读取来源
- 测试代码同步更新

### 6. `AGENT_KB_DATABASE_URL` 保留
- 不重命名，不添加 fallback，不改变现有 env var 约定

### 7. Guest 保持不变
- 硬编码密码 `guest`
- 读权限：可读 `app.profiles`（所有），不可读 `auth.accounts`（除自己）
- 不可读 `auth.registration_tokens`（已有 RLS 保护）

## Acceptance Criteria

- [ ] `app.profiles` 表创建成功，含 account_id UNIQUE 约束
- [ ] `auth.accounts` 不包含 `principal_type` 和 `display_name` 列
- [ ] `auth.accounts` SELECT RLS：普通用户只能看自己
- [ ] `app.profiles` SELECT RLS：所有人可读
- [ ] `app.profiles` UPDATE RLS：只能改自己的
- [ ] `register_with_token` 创建 account 和 profile 两行
- [ ] Guest 不能读 `auth.accounts` 其他行
- [ ] Guest 能读所有 `app.profiles`
- [ ] `register_with_token` 注释符合实际行为（仅 guest）
- [ ] 所有引用 `auth.accounts.display_name` 的 SQL/Python 代码已更新
- [ ] 所有引用 `auth.accounts.principal_type` 的代码已更新
- [ ] `AGENT_KB_DATABASE_URL` 名称未改动
- [ ] 测试全部通过

## Definition of Done

- Tests 通过（live flow tests）
- lint / typecheck 无新增问题
- `register_with_token` 端到端可用（guest → token → 新 account + profile）

## Technical Approach

### Schema 变更（`postgres/init/001-united-agent.sql`）

1. `auth.accounts` 去 `principal_type`, `display_name`
2. 新表 `app.profiles`
3. `auth.accounts` RLS SELECT 改为 `(id = auth.current_account_id() OR auth.is_admin())`
4. `app.profiles` RLS 三条策略
5. `auth.register_with_token()` 插入两表
6. 移除 `auth.registration_tokens` 上的 `SELECT` GRANT （已有 RLS 保护，撤回 GRANT 更干净）
7. Guest GRANT 从 `SELECT ON ALL TABLES IN SCHEMA auth` 改为表级精确 GRANT（仅 `auth.accounts(id, pg_login_role)` 自己的行 + `app.profiles` 全部）

### Python 脚本变更

- `register_with_token.py`：适配新 schema
- `_postgres_connect_common.py`、`_postgres_admin_common.py`：如有 `display_name` 引用需更新
- `manage_registration_token.py`：如有引用需更新

### 测试变更

- `test_registration_token_live_flows.py`
- `test_postgres_connect_tooling.py`
- `test_postgres_admin_tooling.py`
- `test_agent_kb_postgres_skeleton.py`
- 其他引用 `display_name` 或 `principal_type` 的测试

## Decision (ADR-lite)

**Context**: `auth.accounts` 混合了内部身份字段和公开资料字段，guest/普通用户可见性太高。
**Decision**: 拆分为 `auth.accounts`（内部） + `app.profiles`（公开），通过 RLS 分别控制访问。
**Consequences**: 所有引用 `display_name`/`principal_type` 的代码需加 JOIN；公开信息查询走 `app.profiles`。

## Out of Scope

- Guest 密码去硬编码（保留）
- `AGENT_KB_DATABASE_URL` 重命名（保留）
- `app.profiles` 加更多字段（bio 已在范围内）
- 前端代码（仅后端 SQL + Python）

## Technical Notes

### 受影响的文件

| 文件 | 变更类型 |
|---|---|
| `postgres/init/001-united-agent.sql` | Schema + RLS + 函数重构 |
| `skills/agent-kb-postgres-connect/scripts/register_with_token.py` | 适配新 schema |
| `skills/agent-kb-postgres-connect/scripts/_postgres_connect_common.py` | 如有引用需更新 |
| `skills/agent-kb-postgres-admin/scripts/_postgres_admin_common.py` | 如有引用需更新 |
| `skills/agent-kb-postgres-admin/scripts/manage_registration_token.py` | 如有引用需更新 |
| `skills/agent-kb-postgres-connect/SKILL.md` | 文档更新 |
| `skills/agent-kb-postgres-admin/SKILL.md` | 文档更新 |
| `tests/test_registration_token_live_flows.py` | 适配新 schema |
| `tests/test_postgres_connect_tooling.py` | 适配新 schema |
| `tests/test_postgres_admin_tooling.py` | 适配新 schema |
| `tests/test_agent_kb_postgres_skeleton.py` | 适配新 schema |
| `tests/test_board_post_live_flows.py` | 如有引用需更新 |
| `tests/test_connect_skill_live_flows.py` | 如有引用需更新 |
| `.trellis/spec/backend/database-guidelines.md` | 更新 env var 约定（如需） |
| `docs/developer-guide.md` | 更新文档 |
| `README.md` | 更新文档 |

### 研究参考资料

- [`research/guest-rls-and-registration-audit.md`](research/guest-rls-and-registration-audit.md) — 当前 guest RLS 和注册流程完整审计
