# brainstorm: chinese readme rewrite

## Goal

将仓库根目录 `README.md` 重写为中文版本，并把项目定位明确收敛为：这是一个无 Web UI、无应用 API、以 PostgreSQL 数据库本身为交付物和部署单元的系统。

## What I already know

* 用户希望先重写 `README.md`。
* 用户明确要求 README 用中文。
* 用户明确要求 README 体现系统设计为无 Web UI、无 API。
* 用户明确要求 README 体现部署只需要数据库。
* 当前 `README.md` 已经说明项目没有 application server 或 web UI，但仍然使用了较多英文说明，并保留了较宽泛的“project skeleton”表述。
* 当前仓库已经包含 PostgreSQL bootstrap、管理脚本、distributed skills、测试。

## Assumptions (temporary)

* README 仍然需要保留实际可运行方式、目录结构、管理脚本和技能文件的说明。
* README 需要更明确地把系统描述为“数据库即系统边界”，而不是“未来会补 API/UI 的半成品后端”。

## Open Questions

* 无

## Requirements (evolving)

* 将根目录 `README.md` 重写为中文。
* 明确写出系统没有 Web UI。
* 明确写出系统没有应用 API。
* 明确写出部署仅依赖数据库。
* 文档内容应与当前仓库真实状态一致。
* README 结构采用“系统定位优先，其次给最小可用操作说明”的平衡方案。
* README 内容深度采用平衡版：除系统定位、启动数据库、连接验证外，还保留账号创建、版主管理与 skills 使用入口。

## Acceptance Criteria (evolving)

* [ ] `README.md` 主要内容为中文。
* [ ] `README.md` 明确说明系统无 Web UI、无 API。
* [ ] `README.md` 明确说明部署只需要 PostgreSQL 数据库。
* [ ] `README.md` 中的运行说明与仓库当前结构一致。
* [ ] `README.md` 保留最小但完整的可操作入口：启动、连接、验证、账号创建、版主管理、skills 入口。

## Definition of Done (team quality bar)

* Tests added/updated if documentation contracts change
* Existing tests remain green
* Docs/notes updated if behavior or positioning changes

## Out of Scope (explicit)

* 修改数据库 schema
* 新增 API 或 UI
* 调整 Python 管理脚本行为
* 将 README 改写成纯运维手册

## Technical Approach

* README 顶部先定义系统边界：它是一个以 PostgreSQL 为核心交付物的系统，而不是等待补齐 Web/API 的半成品后端。
* 中段说明当前仓库已经提供的能力：schema bootstrap、RLS、账号/权限管理脚本、skills、测试。
* 后段只保留与当前系统边界一致的最小必要操作说明，例如启动数据库、连接数据库、验证 bootstrap 账号、创建账号与版主管理入口。

## Decision (ADR-lite)

**Context**: README 既要纠正项目定位，又不能失去可操作性。

**Decision**: 采用“定位优先、操作其次”的平衡结构，先定义这是一个无 Web UI、无应用 API、仅需数据库部署的系统，再提供最小必要的部署和操作说明。

**Consequences**: README 会更像系统说明书而不是泛化的开发脚手架介绍；同时仍保留足够的启动和管理信息，避免用户只看到抽象定位却不知道如何实际使用。

**Follow-up decision**: 内容深度采用平衡版，不退化成只有启动命令的极简首页，也不保留当前 README 那种偏长的全量英文说明。

## Technical Notes

* Target file: `/home/jerry/code/united_agent/README.md`
* Current README already documents Docker Compose + PostgreSQL 16 bootstrap as the supported path.
* Existing tests reference README content, so README wording changes may require test updates.
