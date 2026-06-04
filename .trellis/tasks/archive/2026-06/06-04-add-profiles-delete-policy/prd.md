# Add profiles DELETE policy migration SQL

## Goal

补上 `app.profiles` 缺失的 DELETE RLS policy，使 `auth.delete_managed_account()` 的 FK CASCADE 能正确级联删除 profile 行（当前因 `FORCE ROW LEVEL SECURITY` + 无 DELETE policy 被拦断）。

## What I already know

- `app.profiles` 有 `FORCE ROW LEVEL SECURITY`（001:785）
- 已定义了 SELECT / INSERT / UPDATE 三个策略（001:795-806），**缺 DELETE**
- `delete_managed_account()` 是 `SECURITY DEFINER`，但 `FORCE RLS` 仍然会对 CASCADE 生效
- 项目使用 `postgres/init/NNN-slug.sql` 命名约定，通过 Docker entrypoint 按字母序执行
- 对已运行的数据库需手动打补丁（Docker entrypoint 不会重跑 init）

## Requirements

1. 创建 `postgres/init/002-add-profiles-delete-policy.sql`，内容：
   ```sql
   CREATE POLICY profiles_delete_admin ON app.profiles
     FOR DELETE TO united_agent_user
     USING (true);
   ```
2. 用 `docker compose exec` 对运行中的库打补丁
3. 同步更新 `001-united-agent.sql` 中 RLS policy 区块，原地也补上 DELETE policy（保持 001 完整，避免 fresh init 时遗漏）

## Acceptance Criteria

- [ ] `postgres/init/002-add-profiles-delete-policy.sql` 存在，内容正确
- [ ] `001-united-agent.sql` 中 profiles RLS 区块包含 DELETE policy
- [ ] 运行中数据库的 `app.profiles` 有 `profiles_delete_admin` policy
- [ ] 账号删除后 profile 行跟着消失

## Definition of Done

- 迁移文件创建，格式符合 `NNN-slug.sql`
- 001 同步更新
- 运行中数据库已打补丁
- 验证删除流程：profile 随账号一起清

## Out of Scope

- 不修改 `delete_managed_account()` 函数体（不必加显式 DELETE FROM app.profiles）
- 清理孤儿 profile 行（用户自行通过 admin 工具处理）

## Technical Notes

- 001:784-806 当前 profiles RLS 区域
- 目录规范：`.trellis/spec/backend/directory-structure.md` 定义了 `NNN-project-slug.sql` 命名约定
- Docker entrypoint 按字母序执行 `postgres/init/*.sql`
