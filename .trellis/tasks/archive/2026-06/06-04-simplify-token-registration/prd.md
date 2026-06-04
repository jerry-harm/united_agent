# Remove SHA-256 hashing from registration tokens

## Goal

去掉注册 token 流程中的 SHA-256 哈希层：`registration_tokens` 表直接存原始 token，`register_with_token()` 用明文比对，Python 脚本不再做客户端 hash。简化后 psql 也能直接调用注册函数。

## Requirements

### Schema 变更
- `registration_tokens.token_hash` → 重命名为 `token`（UNIQUE 约束保持）
- 删除 `registration_tokens.token_preview` 列（现在可直接看 token）
- 索引 `idx_registration_tokens_active_lookup` 从 `token_hash` 改为 `token`

### SQL 函数变更
- `issue_registration_token(p_token_hash, p_token_preview, ...)` → 改为 `(p_token, ...)`，去掉 preview 参数
- `register_with_token(p_token_hash, ...)` → 改为 `(p_token, ...)`，内部 `WHERE token = p_token` 直接比对

### Python 脚本变更
- `register_with_token.py`：删除 `hashlib.sha256(...)` 行，传原始 token
- `manage_registration_token.py`：删除 `hashlib.sha256(...)` 行，不再生成 `token_preview`

### 测试
- `test_registration_token_live_flows.py`：适配新参数名和逻辑
- `test_agent_kb_postgres_skeleton.py`：更新列名断言

## Acceptance Criteria

- [ ] `registration_tokens` 列 `token` 存在，`token_hash` 和 `token_preview` 不存在
- [ ] `register_with_token('raw-token', ...)` 用明文 token 直接注册成功
- [ ] `register_with_token.py` 无 `hashlib` import
- [ ] `manage_registration_token.py` 无 `hashlib` import
- [ ] 所有测试通过

## Out of Scope

- psql 示例文档（另一个 task）
- token 生成方式（保留 `secrets.token_urlsafe(24)`）

## Technical Notes

- 受影响文件：`postgres/init/001-united-agent.sql`, `register_with_token.py`, `manage_registration_token.py`, `test_registration_token_live_flows.py`, `test_agent_kb_postgres_skeleton.py`, `test_postgres_connect_tooling.py`, `test_postgres_admin_tooling.py`, SKILL.md × 2, README, 相关 spec
- Token 唯一性由 `token` 列 UNIQUE 约束保证
- `secrets.token_urlsafe(24)` 生成 184-bit 随机字符串，碰撞概率几乎为零
