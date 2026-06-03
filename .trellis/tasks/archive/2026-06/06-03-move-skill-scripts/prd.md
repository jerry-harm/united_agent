# move skill scripts under skill directories

## Goal

把当前由 skill 直接依赖的项目根目录脚本迁移到对应 skill 目录下，让 skill 自包含其执行所需脚本与 SQL，确保 skill 可独立安装使用；项目根部 `scripts/` 仅保留数据库维护或人工调用入口。

## What I already know

* 用户明确要求：skill 用到的 script 应放在 skill 目录下面，而不是项目根部新建或继续依赖一个公共 `scripts/` 目录。
* 用户进一步明确：凡是被 skill 调用的脚本都必须做成自包含，否则用户安装 skill 后无法使用。
* 当前主要命中点是 `skills/agent-kb-postgres-admin/SKILL.md`，它直接引用 `scripts/create_principal.py`、`scripts/manage_board_moderator.py` 以及 `scripts/sql/*.sql`。
* 仓库根部 `scripts/` 可以继续保留，但定位应收敛为数据库维护或人工调用入口，而不是 skill 的安装时依赖。
* README 也把这些根目录脚本作为公开入口进行说明，因此迁移如果落地，文档与测试大概率需要同步。

## Assumptions (temporary)

* 本次优先处理 `agent-kb-postgres-admin` 这个已确认直接依赖根目录脚本的 skill。
* `agent-kb-postgres-connect` 当前不依赖根目录脚本，可暂不变动，除非后续检查发现引用。
* 如果根部 `scripts/` 仍需保留同类能力，它们可以继续存在，但 skill 侧不能再通过这些根部路径作为运行前提。

## Open Questions

* None.

## Requirements (evolving)

* `agent-kb-postgres-admin` 的执行说明和实现入口改为位于 skill 目录内部。
* skill 内部资源目录采用 `skills/<skill>/scripts/` 与 `skills/<skill>/scripts/sql/`。
* skill 运行所需的 Python/SQL 资源与 skill 一起存放，避免继续把项目根目录 `scripts/` 当作 skill 的运行前提。
* 任何被 skill 文档调用或依赖的脚本都必须随 skill 一起分发。
* 改动应保持现有管理能力不退化：创建账号、管理 board moderator、读取对应 SQL。
* 根部 `scripts/` 若继续保留，只承担数据库维护或人工调用用途，不再作为 skill 使用说明中的默认入口。
* 相关文档与测试需要和实际入口保持一致。

## Acceptance Criteria (evolving)

* [ ] `skills/agent-kb-postgres-admin/SKILL.md` 不再引用项目根目录 `scripts/...` 作为操作入口。
* [ ] skill 目录下存在可对应执行的脚本/SQL 结构。
* [ ] skill 所需脚本在脱离仓库根目录 `scripts/` 的前提下仍可被 skill 文档直接调用。
* [ ] 相关 README / tests / docs 中与 skill 入口相关的描述已同步。
* [ ] 验证命令通过，至少覆盖受影响测试或静态检查。

## Definition of Done (team quality bar)

* Tests added/updated (unit/integration where appropriate)
* Lint / typecheck / CI green
* Docs/notes updated if behavior changes
* Rollout/rollback considered if risky

## Out of Scope (explicit)

* 不重构与 skill 无关的数据库管理脚本。
* 不强制删除根部现有 `scripts/` 中仍合理的人工维护入口。
* 不额外引入新的全局脚本目录结构。

## Technical Notes

* Confirmed file: `skills/agent-kb-postgres-admin/SKILL.md`
* Confirmed shared script location today: `scripts/`
* Likely impacted docs: `README.md`
* Likely impacted tests/spec assertions: any tests that assert skill commands or documented paths
* Scope clarification: skill-bundled scripts are required for installability; repo-root scripts may remain for manual maintenance workflows

## Decision (ADR-lite)

**Context**: skill 当前直接调用仓库根目录 `scripts/`，会让 skill 安装后缺少运行时资源。

**Decision**: 将 skill 依赖的 Python/SQL 资源内聚到 `skills/agent-kb-postgres-admin/scripts/` 与 `skills/agent-kb-postgres-admin/scripts/sql/`，并把 skill 文档入口切到这些本地路径。根部 `scripts/` 继续保留给数据库维护或人工调用用途。

**Consequences**: skill 变为可分发、自包含；README 与测试需要同步更新；根部脚本与 skill 脚本的职责边界会更清晰。
