# 补齐数据库权限 live 测试

## Goal

补齐当前仓库中对 PostgreSQL 权限设计的 live 集成测试，让关键授权入口和高风险权限变更路径不仅有静态契约断言，也有真实数据库执行证据，降低 helper/脚本/SQL/RLS 之间出现语义漂移而未被发现的风险。

## What I already know

* 现有 live 测试文件只有 `tests/test_board_post_live_flows.py` 和 `tests/test_connect_skill_live_flows.py`。
* `tests/test_board_post_live_flows.py` 已覆盖普通用户发帖成功、普通用户创建 board 被拒、普通用户直接写 `auth.board_moderators` 与 `auth.principal_global_roles` 被拒、成为版主后可以更新 `app.posts.verification`。
* `tests/test_connect_skill_live_flows.py` 已覆盖 connect script 成功路径、未映射 login 失败、disabled 账号失败。
* `tests/test_postgres_admin_tooling.py` 和 `tests/test_postgres_connect_tooling.py` 主要是静态/契约测试，不是完整的 live 权限验证。
* README 已把当前 live 测试定位为仓库关键路径的一部分，并明确 board/post live test 以直接 SQL 为主验证真实权限链路。

## Assumptions (temporary)

* 本任务的重点是补齐数据库权限设计的 live 测试，而不是重构权限模型本身。
* 测试仍应基于本地 PostgreSQL / `docker compose` 环境，可在缺少 `psycopg` 或数据库时跳过。
* 用户已确认本轮按“全面覆盖”推进，不只补最小高风险集合。

## Open Questions

* 当前无阻塞性未决问题；待用户确认完整需求摘要后进入实现准备。

## Requirements (evolving)

* 保留现有 live 测试风格：真实连接 PostgreSQL，尽量以直接 SQL 作为权限结论依据。
* 新增 live 测试应覆盖当前缺失的高风险权限路径与关键权限矩阵，而不只停留在最小冒烟级别。
* 新增 live 覆盖按权限主题拆成新的测试文件，而不是继续堆叠进单个已有 live 文件。
* live 覆盖至少应包含：
  * `create_principal.py` 的真实授权矩阵（谁能创建什么角色、谁不能创建）
  * `manage_board_moderator.py` 的脚本级端到端授权路径
  * 版主授权撤销后的权限立即失效
  * disabled / inactive 账号在关键写路径上的权限退化
  * 普通用户对关键内容表的 `update/delete` 边界，作为本轮更主要的权限覆盖重点
  * 普通用户对关键内容表的读取边界（`read` 也要覆盖，至少覆盖 post read 的可见性/可读性预期）
  * 除 `boards + posts` 外，也纳入 `review_entries / review_history / tags` 等内容表的关键权限边界
  * 关键 helper 返回值与真实 SQL 允许/拒绝结果的一致性验证
* 测试清理逻辑必须能回收创建的账号、角色、board、post、授权记录，避免相互污染。
* README/测试入口说明如果发生变化，需保持与仓库现状一致。

## Acceptance Criteria (evolving)

* [ ] 针对数据库权限设计缺口新增成体系的 live 测试，而不是仅新增静态断言。
* [ ] 新增测试能在本地 PostgreSQL 环境下真实执行，并对允许/拒绝结果做显式断言。
* [ ] 新增 live 测试按权限主题拆分，单文件职责清晰，失败时能快速定位到具体权限面。
* [ ] `python3 -m unittest discover -s tests -v` 通过。

## Technical Approach

* 延续当前 `unittest + psycopg + 本地 PostgreSQL` 的 live 测试模式。
* 复用现有 live 测试里的环境装载、admin/principal 连接、清理策略等模式，避免引入新的测试基础设施。
* 按权限主题拆分新增 live 文件，分别承载：账号创建授权矩阵、版主管理脚本端到端、账号状态退化/撤销后的权限收缩，以及普通用户在 `boards / posts / review_entries / review_history / tags` 等内容表上的 `read/update/delete` 边界场景。
* 对脚本入口类权限测试，优先直接调用仓库内已交付脚本；对数据库最终授权结论，优先以直接 SQL 的允许/拒绝结果为准。

## Decision (ADR-lite)

**Context**: 当前仓库只有少量 live 测试，且 board/post 权限、connect 身份验证、admin 脚本授权矩阵混杂风险正在上升。若继续把更多场景堆入现有文件，setup/teardown 和断言语义会变得难以维护。

**Decision**: 本轮按“全面覆盖”补齐数据库权限 live 测试，并按权限主题拆分新的 live 测试文件，而不是只补 2-3 个最小场景或继续把场景堆进已有 live 文件。

**Consequences**: 测试入口数量会上升，但每个文件的权限边界更清晰，失败定位更直接，也更利于后续继续扩展授权矩阵。

## Definition of Done (team quality bar)

* Tests added/updated (unit/integration where appropriate)
* Lint / typecheck / CI green
* Docs/notes updated if behavior changes
* Rollout/rollback considered if risky

## Out of Scope (explicit)

* 修改数据库权限模型本身
* 引入新的测试框架
* 为所有 SQL helper 做穷尽式权限矩阵验证（除非本轮确认纳入范围）

## Technical Notes

* 关键文件：
  * `tests/test_board_post_live_flows.py`
  * `tests/test_connect_skill_live_flows.py`
  * `tests/test_postgres_admin_tooling.py`
  * `tests/test_postgres_connect_tooling.py`
  * `skills/agent-kb-postgres-admin/scripts/create_principal.py`
  * `skills/agent-kb-postgres-admin/scripts/manage_board_moderator.py`
  * `postgres/init/001-united-agent.sql`
* README 当前明确记录了两组 live 测试入口，其中 board/post 测试以直接 SQL 为主，connect 测试以 `verify_connection.py` 为真实入口。
