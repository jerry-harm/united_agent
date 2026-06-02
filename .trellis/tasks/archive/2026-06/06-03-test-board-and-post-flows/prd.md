# test board and post flows

## Goal

对当前 PostgreSQL-first MVP 的核心业务链路做一轮真实操作测试，覆盖 board 创建、post 发布，以及与之相邻的权限/RLS 行为，确认数据库现在不只是“能建账号”，也能按预期承载基础内容流转。

## What I already know

* 当前数据库使用 `auth` / `app` 双 schema，身份解析依赖 `session_user` 映射到 `auth.accounts`。
* `app.boards` 的插入策略要求：`auth.is_admin() AND auth.can_write() AND created_by = auth.current_account_id()`。
* `app.posts` 的插入策略要求：`auth.can_write()`、`author_id = auth.current_account_id()`、`verification = 'progressing'`。
* `app.posts` 的更新策略要求：`auth.can_write()` 且操作者是 `admin` 或对应 board 的 moderator。
* `review_entries` 只能由本人插入/更新，`review_history` 仅 admin 可查。
* 当前本地 Docker/PostgreSQL 已经能通过 `create_principal.py` 正确创建真实登录账号并完成身份映射。

## Assumptions (temporary)

* 本任务以“真实数据库操作验证”为主，可能先以命令/脚本形式复现，不一定一开始就新增自动化测试文件。
* 需要至少覆盖一条 admin 创建 board、normal_user 发 post 的主路径。

## Open Questions

* None currently.

## Requirements (evolving)

* 验证 admin 可以创建 board。
* 验证普通用户可以在允许条件下发布 post。
* 验证关键 RLS/权限边界至少有一条反例检查，例如普通用户不能创建 board。
* 补一个自动化测试，优先覆盖脚本/真实数据库交互链路，而不是只做静态断言。
* 自动化测试可以依赖一个已经运行中的本地 PostgreSQL / `docker compose` 环境。

## Technical Approach

先用真实数据库链路跑通 admin 创建 board、normal_user 发布 post，以及至少一条拒绝路径；然后把这组操作沉淀成可重复执行的自动化集成测试，测试前提明确为本地 Docker/PostgreSQL 已启动。

## Acceptance Criteria (evolving)

* [ ] 至少完成一次真实 board 创建，并确认写入结果正确。
* [ ] 至少完成一次真实 post 发布，并确认作者映射与初始 verification 正确。
* [ ] 至少验证一条不允许的操作被数据库拒绝。

## Definition of Done (team quality bar)

* Tests added/updated (unit/integration where appropriate)
* Lint / typecheck / CI green
* Docs/notes updated if behavior changes
* Rollout/rollback considered if risky

## Out of Scope (explicit)

* 新增 Web UI 或应用 API。
* 重构 schema / RLS 设计，除非测试直接暴露 bug。
* 覆盖全部业务表的完整集成测试矩阵。

## Technical Notes

* 关键 schema / policy 定义：`postgres/init/001-united-agent.sql`
* 当前操作说明与关系图：`README.md`
