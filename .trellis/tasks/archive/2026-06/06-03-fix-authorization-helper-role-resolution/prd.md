# fix authorization helper role resolution

## Goal

修复当前权限系统中角色解析错误的问题，并验证数据库里的权限 helper、RLS 策略与真实业务权限是否一致，确保 `normal_user` 不会被误识别为 `admin` / `super_admin`，以及关键写操作只对正确角色开放。

## What I already know

* 在 `tests/test_board_post_live_flows.py` 的 live 集成测试中，原本预期 `normal_user` 创建 board 会被拒绝，但实际没有被拒绝。
* 真实复现时，一个通过 `scripts/create_principal.py` 创建的 `normal_user` 账号返回：
  * `auth.is_admin() = true`
  * `auth.is_super_admin() = true`
  * `auth.can_write() = true`
* `app.boards` 当前的 INSERT RLS 策略表面上是正确的：`auth.is_admin() AND auth.can_write() AND created_by = auth.current_account_id()`。
* `app.boards` 已启用 `ENABLE ROW LEVEL SECURITY` 且 `FORCE ROW LEVEL SECURITY`。
* 高概率根因在 `auth.has_global_role(role_name)` 的 SQL 实现，参数名与列名同名，可能导致“检查指定角色”退化成“只要有任意 global role 记录就返回 true”。

## Assumptions (temporary)

* 这不是单一业务表策略问题，而是权限 helper 实现 bug，影响面可能覆盖 `boards`、`board_moderators`、`principal_global_roles`、`posts_update_verification` 等依赖 `auth.is_admin()` / `auth.is_super_admin()` 的路径。
* 修复应优先落在 helper 函数实现与对应回归测试，而不是在业务表策略上打补丁规避。

## Open Questions

* None currently.

## Requirements (evolving)

* 修复角色 helper 的错误解析。
* 证明 `normal_user` 不再被识别为 `admin` 或 `super_admin`。
* 验证依赖 `admin` / `super_admin` 的核心写路径在修复后名实一致，至少覆盖 `boards`、`board_moderators`、`principal_global_roles`、`posts_update_verification`。
* 集成测试必须以直接 SQL 操作为主来验证数据库原生权限约束，不能只依赖 skill / helper script 入口是否成功。

## Technical Approach

优先修正 `auth.has_global_role(...)` 及其依赖链，然后通过 live 集成测试和必要的静态断言双重验证权限系统：既验证 helper 返回值本身，也验证关键写路径在真实数据库中的授权结果与设计一致。除必须用脚本建立前置条件的场景外，权限验证应优先直接执行 SQL，以证明数据库本身而不是运维入口承担了真实安全边界。

## Acceptance Criteria (evolving)

* [ ] `normal_user` 会返回 `auth.is_admin() = false`。
* [ ] `normal_user` 会返回 `auth.is_super_admin() = false`。
* [ ] `normal_user` 创建 board 被拒绝。
* [ ] bootstrap `super_admin` 创建 board 仍然成功。
* [ ] 回归测试覆盖 helper 解析与至少一条真实权限写路径。

## Definition of Done (team quality bar)

* Tests added/updated (unit/integration where appropriate)
* Lint / typecheck / CI green
* Docs/notes updated if behavior changes
* Rollout/rollback considered if risky

## Out of Scope (explicit)

* 重做整个 auth/app 模型。
* 引入新的权限体系概念。
* 扩展到与本 bug 无关的 UI/API 层。

## Technical Notes

* 关键文件：
  * `postgres/init/001-united-agent.sql`
  * `tests/test_board_post_live_flows.py`
  * `tests/test_agent_kb_postgres_skeleton.py`
  * `tests/test_postgres_admin_tooling.py`
* 当前 live test 已经提供了真实证据，说明这是实现级漏洞，不是单纯测试预期错误。
