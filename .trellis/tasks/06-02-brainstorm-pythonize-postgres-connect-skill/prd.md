# brainstorm: pythonize postgres connect skill

## Goal

把 `skills/agent-kb-postgres-connect/SKILL.md` 调整为与 `skills/agent-kb-postgres-admin/SKILL.md` 同一风格，但职责边界改为面向普通用户的连接与身份验证：不负责创建账号、不负责特权管理、不调用 `psql`，而是通过 Python/`psycopg` 风格说明普通用户如何验证自己拿到的账号是否可用。同时先审视当前两个 skill 的职责边界与功能是否已经足够。

## What I already know

* 用户要求在写 skill 之前先参考 `skill-creator` 的方法。
* 用户要求 `agent-kb-postgres-connect` 也“用 python 写”，并和 `agent-kb-postgres-admin` 保持同一风格。
* 用户最新明确要求：给普通用户用的 connect skill 不做创建账号之类的事情。
* 用户对是否新建脚本的判断标准是：如果逻辑很短，不必新建脚本；但如果 skill 内嵌代码已经不比脚本调用更短，就应考虑抽成脚本。
* 当前 `agent-kb-postgres-connect` 还是以 `psql` 和手写 SQL 片段为主，没有 `compatibility` 字段，也没有强调 `psycopg` 依赖。
* 当前 `agent-kb-postgres-admin` 已经采用更统一的风格：有 `compatibility`、有 `pip install "psycopg[binary]"`、优先指向 `scripts/create_principal.py` / `scripts/manage_board_moderator.py`。
* 当前 `agent-kb-postgres-connect` 的现状职责是：连接到已运行实例、创建专属登录账号、重新连接、验证身份映射。
* 当前测试 `tests/test_agent_kb_postgres_skeleton.py` 仍然断言 `agent-kb-postgres-connect` 含有旧的 `psql + SQL` 说明。
* 仓库里已经有后续设计痕迹表明 connect/admin 边界在演化：
  * `06-02-postgres-admin-skill` 的目标是把特权账号管理集中到 admin skill
  * 当前 `README.md` 仍然把 connect skill 描述成会“创建登录账号”，这和用户现在想要的普通用户定位冲突

## Assumptions (temporary)

* 这里的“用 python 写”主要指 skill 中的推荐操作流改为 Python 脚本驱动，而不是把 skill 本体从 Markdown 改成 Python。
* `agent-kb-postgres-connect` 和 `agent-kb-postgres-admin` 仍应维持不同职责：前者偏普通用户连接/验证，后者偏特权管理。

## Open Questions

* 无

## Requirements (evolving)

* 在修改前明确现有两个 skill 的职责边界和当前不足。
* `agent-kb-postgres-connect` 的文档风格要与 `agent-kb-postgres-admin` 对齐。
* 连接 skill 应彻底改为 Python 化流程。
* 连接 skill 不应调用 `psql` 作为标准操作路径。
* 保留现有 checked-in SQL 文件作为系统实现基础，而不是删除 SQL 文件。
* 连接 skill 不负责创建账号、分配权限或其他特权管理动作。
* 连接 skill 应面向普通用户已经拿到数据库连接信息和账号凭据之后的连接与身份验证场景。
* 是否新增 helper script，取决于验证逻辑长度和复用价值，而不是为了 Python 化机械加脚本。
* 本次实现允许在落地阶段判断：如果普通用户验证逻辑已经值得抽象，就可以新增一个很小的 Python helper；否则只改 skill 文案。
* 文档必须与当前仓库真实能力一致。
* 如 skill 文案契约变化影响测试，需要同步更新测试。

## Acceptance Criteria (evolving)

* [ ] `agent-kb-postgres-connect` 是否足够、还缺什么，在 PRD 中被明确描述。
* [ ] `agent-kb-postgres-connect` 与 `agent-kb-postgres-admin` 的风格差异被消除或显著缩小。
* [ ] 连接 skill 使用 Python/`psycopg` 风格描述普通用户操作流程。
* [ ] 连接 skill 不再把 `psql` 作为标准操作路径。
* [ ] 连接 skill 不再承担账号创建职责。
* [ ] 连接验证实现方式与复杂度相称，不为了很短逻辑强行加脚本。
* [ ] 如果新增 helper script，它必须足够小且明显优于把同样逻辑内嵌在 skill 中。
* [ ] skill 文档仍然与仓库中的 SQL 文件和脚本布局一致。
* [ ] 相关测试与新 skill 文案保持一致。

## Technical Approach

* 先清理职责边界：普通用户 connect skill 只负责连接与身份验证，特权账号创建和权限管理完全交给 admin skill。
* 把 connect skill 的文档风格改成与 admin skill 一致的 Python/`psycopg` 风格，并补上相应依赖与边界说明。
* 实现时检查“普通用户验证逻辑”长度：
  * 如果几行 Python 就能讲清楚，则直接内嵌在 skill 中。
  * 如果 skill 内需要写的代码或说明已经不比脚本调用更短，就新增一个小型 helper script，并让 skill 调用它。
* 同步修正当前 README / 测试中对 connect skill 仍然包含“创建账号”职责的陈旧描述。

## Decision (ADR-lite)

**Context**: 当前 connect skill 继承了早期设计，仍把账号创建和连接验证混在一起；但后续 admin skill 已经承担了特权管理角色，导致职责重叠。

**Decision**: 把 connect skill 收敛为普通用户连接/验证入口，不再承担账号创建；同时允许实现阶段根据逻辑长度决定是否新增极小 Python helper，而不是预先强制一律内嵌或一律抽脚本。

**Consequences**: 两个 skill 的边界会更清楚，普通用户路径更干净；但需要同步更新 skill 契约测试和可能的 README 文案，消除旧设计残留。

## Definition of Done (team quality bar)

* Tests added/updated if skill contracts change
* Existing tests remain green
* Docs/notes updated if behavior or positioning changes

## Out of Scope (explicit)

* 修改数据库 schema
* 新增 Web UI 或 API
* 无依据地扩大两个 skill 的职责边界
* 把普通用户 connect skill 重新做成特权管理入口

## Technical Notes

* Target files likely include:
  * `skills/agent-kb-postgres-connect/SKILL.md`
  * `tests/test_agent_kb_postgres_skeleton.py`
  * possibly `README.md` if skill-facing wording needs alignment
* Current connect skill hardcodes SQL examples against:
  * `auth.accounts`
  * `auth.create_account_login(...)`
  * `auth.principal_global_roles`
  * `psql` connection strings
* Current admin skill already documents:
  * `compatibility`
  * `psycopg`
  * `pip install "psycopg[binary]"`
  * Python entrypoints under `scripts/`
* Earlier repo docs/design show a now-stale overlap:
  * connect skill originally included account creation from admin session
  * later admin skill design centralized privileged management there
  * current task should remove that overlap explicitly
