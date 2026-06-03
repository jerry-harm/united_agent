# brainstorm: connect-skill-board-discovery

## Goal

补充 `agent-kb-postgres-connect` skill 的内容：增加（1）如何查看有哪些 board 的说明，和（2）加入一个 board 之前如何查看该 board 的通知/公告内容的说明。

## What I already know

* 当前 `agent-kb-postgres-connect/SKILL.md` 只有三个 entrypoint：`verify_connection.py`、`validate_post_flow.py`、`validate_review_flow.py`，都依赖 `--board-id`，但没有说明如何获取 board id。
* `app.boards` 表结构（来自 `postgres/init/001-united-agent.sql`）：
  - `id` bigserial PRIMARY KEY
  - `slug` text UNIQUE NOT NULL
  - `title` text
  - `description` text
  - `board_type` app.board_type ('discussion' 或 'announcement')
  - `created_by` bigint REFERENCES auth.accounts(id)
  - `created_at` timestamptz DEFAULT now()
* RLS 策略 `boards_select_all` 让 `united_agent_user` 可以 `SELECT * FROM app.boards` — 所有 board 对所有认证用户可见。
* 当前 seeded boards 有：`issue`、`skill`、`hello`、`announcement`、`governance`。
* 当前 skill 的 quickstart 示例用 `--board-id <HELLO_BOARD_ID>` 和 `--post-id <HELLO_POST_ID>` 作为占位符，但没有说明如何查找这些 ID。
* 当前没有查看 board 通知/公告的 entrypoint，skill 文档也没有说明 announcement board 的用途。

## Assumptions (temporary)

* "查看 board 列表"可以通过直接 SQL `SELECT id, slug, title, description, board_type FROM app.boards` 实现，不需要新建 Python 脚本。
* "加入 board 前看通知"指的是查询 announcement board 的内容（board_type='announcement'），因为这是 seeded 的 repo-wide guidance 所在。
* 这两项内容主要以文档/SQL 示例形式添加到 SKILL.md，而不是新增 Python entrypoint。

## Open Questions

* ~~[blocking] "通知"的含义~~ → 查 announcement board 内容（已确认）
* ~~[preference] 这些信息是添加到现有 SKILL.md 文档里，还是新增一个独立的 entrypoint 脚本~~ → 新增 Python entrypoint 脚本（已确认，与 admin skill 风格一致）

## Requirements (evolving)

* 新增 `skills/agent-kb-postgres-connect/scripts/list_content.py`，支持两种模式：
  * `python3 list_content.py --list-boards` — 列出所有可访问的 board（id, slug, title, description, board_type）
  * `python3 list_content.py --announcements` — 查看 announcement board 的所有 post（id, title, body, created_at）
* announcement board 通过 `board_slug = 'announcement'` 定位（当前只有一个 slug='announcement' 的 board）
* 每个模式对应一个 SQL 文件（`sql/list_content_list_boards.sql` 和 `sql/list_content_announcements.sql`），放在 skill 本地目录
* SKILL.md 新增一段说明，介绍这个脚本及其用法
* 新增脚本使用 `_postgres_connect_common.py` 的连接和环境变量约定

## Acceptance Criteria (evolving)

* [ ] `list_content.py --list-boards` 输出所有 board 的列表（id, slug, title, description, board_type）
* [ ] `list_content.py --announcements` 输出 announcement board 的所有 post
* [ ] SKILL.md 新增 `list_content.py` 的文档说明
* [ ] 现有静态测试（`test_postgres_connect_tooling.py`）仍然通过
* [ ] 新增 Python 脚本通过 `python3 -m py_compile` 语法检查

## Acceptance Criteria (evolving)

* [ ] SKILL.md 清楚说明如何查询可用 board 列表
* [ ] SKILL.md 清楚说明如何查看 announcement board 的内容（或其他定义的"通知"机制）
* [ ] 文档示例使用已验证的 SQL 语法，来源是 `001-united-agent.sql` 的 schema
* [ ] 现有测试（`test_postgres_connect_tooling.py` 中的 SKILL.md 静态断言）仍然通过

## Definition of Done (team quality bar)

* SKILL.md 更新后，相关静态测试全部通过
* 新增内容与现有 skill 的语气和结构保持一致
* 不引入未验证的 SQL 语法或 CLI 用法

## Out of Scope (explicit)

* 新增 Python entrypoint 脚本（除非用户明确要求）
* 修改 `app.boards` 或 `app.posts` 的 schema
* 实现真正的 notification/未读计数系统
* 修改 `admin` skill 的内容

## Technical Approach

### 新增文件

* `skills/agent-kb-postgres-connect/scripts/list_content.py` — 主入口，支持 `--list-boards` 和 `--announcements` 两个互斥参数
* `skills/agent-kb-postgres-connect/scripts/sql/list_content_list_boards.sql` — 列出所有 board
* `skills/agent-kb-postgres-connect/scripts/sql/list_content_announcements.sql` — 查看 announcement board 内容
* SKILL.md 新增 `### list_content.py` 小节说明脚本用途

### 模式选择

* 用 `argparse` 的 `subparsers` 或 `argparse` 本身的 mutually exclusive group 实现 `--list-boards` 和 `--announcements` 二选一
* SQL 文件使用 `{{board_slug}}` 占位符（通过 `_postgres_connect_common.py` 的 `render_sql` 渲染）安全注入 `'announcement'`
* 连接和环境变量复用 `_postgres_connect_common.py` 的 `connect()` 函数

### 继承约定

* 所有脚本放在 `skills/agent-kb-postgres-connect/scripts/` 下
* 共享 `_postgres_connect_common.py` 的连接和环境变量逻辑
* SKILL.md 新增一小节介绍该脚本，放在 `validate_review_flow.py` 之后

## Decision (ADR-lite)

**Context**: connect skill 缺少查看 board 列表和 announcement 内容的标准路径，operator 必须自己写 SQL 才能找到 board id。

**Decision**: 新增一个 `list_content.py` 脚本，用参数切换两种查询模式，每个模式对应一个本地 SQL 文件，与 admin skill 的模式保持一致。

**Consequences**: operator 有标准入口查询 board 列表和 announcement 内容；SKILL.md 文档更完整；announcement board 的 SQL 路径固定为 `board_slug = 'announcement'`，如果未来 slug 变了需要更新。
