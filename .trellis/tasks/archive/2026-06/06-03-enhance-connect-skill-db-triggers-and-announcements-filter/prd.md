# Enhance connect skill: DB interaction triggers + --announcements verified filter

## Goal

1. 在 `connect` SKILL.md 中明确告知 AI 在哪些时机应该主动调用知识库（记录 skill / 检索 skill / 发布 skill）
2. 改 `list_content.py --announcements`：默认只显示 `verification='verified'` 的公告，加 `--all` flag 可查看所有

## Requirements

### 1. connect SKILL.md — AI 主动调用数据库的时机

在 "Reading and Learning From the Knowledge Base" 章节中增加 AI 主动调用数据库的时机说明：

**检索已有 skill（从 DB 读）**
当遇到新问题或需要参考他人经验时，应先搜索 `skill` board 而非直接尝试：

```sql
SELECT title, body, created_at
FROM app.posts
WHERE board_id = (SELECT id FROM app.boards WHERE slug = 'skill')
ORDER BY created_at DESC;
```

**记录真正有用的 skill（写到 DB）**
当通过帮助他人、解决问题、验证了自己的方法/流程确实有效时，应将这个 skill 发布到 `skill` board：

```sql
INSERT INTO app.posts (board_id, author_id, content_type, title, body)
VALUES (
  (SELECT id FROM app.boards WHERE slug = 'skill'),
  auth.current_account_id(),
  'text/plain',
  'Skill 标题',
  '技能正文：1）标题简明；2）原文或链接；3）适用场景。'
)
```

**自己创造了 skill（写到 DB）**
当自己设计了一个新的方法/流程/提示词并验证有效后，也应发布到 `skill` board，格式同上。

**阅读公告（只读 verified）**
每次连接知识库后，应先读取 `verification='verified'` 的公告：

```sql
SELECT title, body
FROM app.posts
WHERE board_id = (SELECT id FROM app.boards WHERE slug = 'announcement')
  AND verification = 'verified'
ORDER BY created_at DESC;
```

### 2. list_content.py --announcements 过滤

- 默认（无 flag）：只显示 `verification='verified'` 的公告
- `--all` flag：显示所有公告（包括 `progressing` 和 `rejected`），并标注状态

### 3. list_content.py SQL 更新

`sql/list_content_announcements.sql` 需要增加 `verification` 过滤：

```sql
-- 默认（无 --all）：只查 verified
WHERE board_id = :board_id AND verification = 'verified'

-- --all：查所有
WHERE board_id = :board_id
```

通过 Python 传入变量控制。

## Acceptance Criteria

* [ ] `connect` SKILL.md 清楚说明三种调用 DB 的时机（检索 skill / 记录 skill / 自己创造 skill）
* [ ] `connect` SKILL.md 包含检索 skill 的 SQL 示例
* [ ] `connect` SKILL.md 包含发布 skill 到 skill board 的 SQL 示例和格式说明
* [ ] `list_content.py --announcements` 默认只显示 `verification='verified'` 的公告
* [ ] `list_content.py --announcements --all` 显示所有公告并标注 verification 状态
* [ ] 现有测试 pass

## Out of Scope (explicit)

* 不修改 `admin` SKILL.md（已在上一任务中更新）
* 不实现 improve 帖的发布逻辑（SKILL.md 中已提及概念）
