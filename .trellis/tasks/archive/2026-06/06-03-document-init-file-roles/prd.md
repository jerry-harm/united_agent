# document-init-file-roles

## Goal

为 `postgres/init/001-united-agent.sql` 补充便于人工审阅的注释，帮助后续逐段检查初始化脚本的职责、权限边界和关键设计约束，同时不改变现有行为。

## What I already know

* 用户已确认注释范围只包含 `postgres/init/001-united-agent.sql`。
* 该文件承担本项目 PostgreSQL 初始化的核心职责：schema/type/table/index/function/trigger/grant/RLS/policy 全部在同一文件中定义。
* 当前文件基本没有面向人工审阅的结构性注释，后续人工检查时阅读成本较高。
* 用户已确认注释粒度选择为：区块级 + 关键函数 + 关键 policy 注释。
* 相关规范要求该文件继续体现双 schema 设计、`session_user` 身份解析、`auth.can_write()` 写权限闸门，以及 RLS 为核心授权边界。

## Assumptions (temporary)

* 本任务以“补说明性注释”为主，不调整 SQL 逻辑、对象命名、权限规则或执行顺序。
* 注释应以段落/区块说明为主，并为关键 helper / RLS policy 补简短说明，而不是为每一行都写解释。
* 注释仅解释当前代码在做什么，不额外展开历史踩坑或调试复盘。

## Open Questions

* 无。

## Requirements (evolving)

* 仅修改 `postgres/init/001-united-agent.sql`。
* 注释要帮助人工审阅者快速理解每一段初始化 SQL 的用途。
* 注释覆盖区块级结构、关键 helper 函数，以及关键 RLS policy。
* 注释只解释当前设计和当前行为，不专门记录历史 bug 或踩坑复盘。
* 不引入行为变化。

## Acceptance Criteria (evolving)

* [ ] `postgres/init/001-united-agent.sql` 增加清晰、准确、可读的说明性注释。
* [ ] 注释后的文件仍保持现有初始化行为不变。
* [ ] 注释覆盖主要结构区块、关键 helper 和关键 policy，便于人工逐段检查。

## Definition of Done (team quality bar)

* SQL 文件改动仅为注释或纯格式整理，不改变语义。
* 如有对应静态测试，完成必要验证。
* 相关说明与任务记录保持一致。

## Out of Scope (explicit)

* 修改 schema 设计、RLS 策略、函数逻辑或权限模型。
* 同步注释其他脚本、README 或测试文件。

## Technical Notes

* 目标文件：`postgres/init/001-united-agent.sql`
* 文件主要区块顺序：schema/bootstrap -> types/tables -> indexes -> helper functions -> triggers -> grants -> RLS/policies。
* 相关规范来源：`.trellis/spec/backend/database-guidelines.md`

## Technical Approach

在不改变 SQL 语义的前提下，为初始化文件补三层说明：

* 区块级注释：标明 bootstrap、schema objects、helper、trigger、grant、RLS/policy 等大段职责
* 关键函数注释：解释身份解析、写权限判断、管理员判断、建账号 helper 的当前职责
* 关键 policy 注释：解释哪些表是全员可读、哪些写入仅限 admin / moderator / account owner

注释文案以“当前系统如何工作”为边界，不写调试历史或失败案例。

## Decision (ADR-lite)

**Context**: 初始化 SQL 文件已经承载项目的大部分数据库契约，但目前缺少适合人工审阅的结构化注释。

**Decision**: 仅在 `postgres/init/001-united-agent.sql` 中增加区块级、关键 helper、关键 policy 注释；注释只解释当前职责，不记录历史坑点。

**Consequences**: 文件可读性会提升，人工审阅更顺畅；同时避免把 init 文件变成过长的事故复盘文档。
