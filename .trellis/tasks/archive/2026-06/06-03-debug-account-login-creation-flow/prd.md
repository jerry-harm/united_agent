# debug account login creation flow

## Goal

定位并修复管理员创建账号时“应用侧账号记录已写入，但 PostgreSQL 可登录角色未可靠创建”的链路问题，确保账号创建后可以立即用对应数据库凭据登录，并能正确映射到 `auth.accounts`。

## What I already know

* 当前本地 `docker compose` 启动后，会自动得到 PostgreSQL 超级用户 `postgres`，以及应用 bootstrap 账号 `Local Postgres Bootstrap -> postgres`。
* `united_agent_user` 是 `NOLOGIN` 共享授权角色，不是终端用户登录账户。
* 当前 schema 中没有针对 `auth.accounts` 的账号创建触发器；账号创建依赖 `scripts/sql/create_principal.sql` 的显式执行链。
* `scripts/sql/create_principal.sql` 当前顺序是：插入 `auth.accounts` -> 调用 `auth.create_account_login(...)` -> 插入 `auth.principal_global_roles`。
* `auth.create_account_login(...)` 是 `SECURITY DEFINER`，owner 为 `postgres`。
* 直接在数据库中调用 `SELECT auth.create_account_login('ua_probe_user', 'ua_probe_pw');` 可以成功创建 PostgreSQL 登录角色。
* 之前曾观察到异常现象：`auth.accounts` 与 `auth.principal_global_roles` 中存在 `ua_test_user` 记录，但 `pg_roles` 中没有 `ua_test_user`。

## Assumptions (temporary)

* 问题更可能在 Python 管理脚本 / SQL 文件执行链 / 事务边界，而不是 PostgreSQL 本身不支持自动创建 role。
* 本任务应以当前 README 记录的管理入口 `scripts/create_principal.py` 为主排查对象。

## Open Questions

* None currently.

## Requirements (evolving)

* 能稳定复现当前账号创建链的实际行为。
* 找到“应用账号已创建但 PostgreSQL 登录角色缺失”的根因。
* 修复后，管理员通过标准入口创建账号时，数据库登录角色必须同步存在且可登录。
* 补上回归测试，覆盖“创建账号后可登录且能正确映射应用身份”的链路。
* 如行为边界或运维前提需要澄清，补充 README 说明。
* 若根因位于数据库函数 / schema 层，允许以最小正确改动直接修改 `postgres/init/001-united-agent.sql`。

## Acceptance Criteria (evolving)

* [ ] 使用 `scripts/create_principal.py` 创建新账号后，`pg_roles` 中存在对应 `LOGIN` 角色。
* [ ] 新创建账号可使用其密码连接 `united_agent` 数据库。
* [ ] 新创建账号连接后，`auth.current_account_id()` 与 `auth.current_account_status()` 返回正确映射。
* [ ] 根因得到解释，不是仅靠临时绕过。

## Definition of Done (team quality bar)

* Tests added/updated (unit/integration where appropriate)
* Lint / typecheck / CI green
* Docs/notes updated if behavior changes
* Rollout/rollback considered if risky

## Out of Scope (explicit)

* 新增独立的 Web UI 或应用 API。
* 重做整个 auth/app 权限模型。
* 扩展到除账号创建链之外的所有管理脚本，除非证据显示它们共享同一根因。

## Technical Notes

* 相关文件：
  * `scripts/create_principal.py`
  * `scripts/_postgres_admin_common.py`
  * `scripts/sql/create_principal.sql`
  * `postgres/init/001-united-agent.sql`
* 已确认 schema 中存在的 trigger 仅用于 `updated_at`、review history、post immutability，不负责账号登录角色创建。

## Technical Approach

先按“脚本入口 -> SQL 文件 -> 数据库函数 -> 事务提交结果”的顺序复现与定位，再在最靠近根因的层做最小修复；如果需要调整 operator 预期或运行前提，同步更新 README，并补上防回归测试。
