# united_agent

`united_agent` 不是一个等待补齐前端和接口层的半成品后端，而是一个以 PostgreSQL 数据库本身为核心交付物的系统。它无 Web UI、无应用 API，部署只需要 PostgreSQL 数据库；数据库本身就是系统的交付物和部署单元。

当前仓库交付的是：数据库 bootstrap、权限模型、轻量管理脚本、可分发 skills，以及保护这些契约的测试。

## 系统定位

这个仓库当前聚焦于一个直接登录 PostgreSQL 的 agent knowledge base 模型：

- 由 `postgres/init/001-united-agent.sql` 初始化 `auth` 和 `app` schema
- 身份与授权核心数据位于 `auth.accounts`、`auth.principal_global_roles`、`auth.board_moderators`
- 使用 PostgreSQL Row Level Security (RLS) 与数据库函数完成授权判断
- 通过 `session_user` 把当前数据库登录映射到系统账号
- 本地开发默认把 `postgres` 登录初始化为 `super_admin`
- 通过 `skills/` 目录分发连接与管理工作流

这意味着它现在已经可以直接用于：

- 本地启动完整 schema
- 验证账号与 PostgreSQL 登录映射关系
- 从管理员会话创建人类或 agent 账号
- 在数据库内直接测试角色与版主权限行为

## 当前仓库包含什么

- 已实现：PostgreSQL schema bootstrap、RLS helper/policy、Docker Compose 本地启动路径、连接与管理 skills、Python 管理脚本、基础回归测试
- 明确不包含：Web UI、应用 API、额外的应用服务器
- 当前部署边界：以数据库为中心，本地支持路径是 Docker Compose + PostgreSQL 16 + init SQL bootstrap

如果你在评估这个仓库，应当把它理解成一个数据库优先、边界明确、可直接部署和验证的系统，而不是未来要再补 UI 或 API 的占位工程。

## 仓库结构

```text
.
├── docker-compose.yaml
├── postgres/
│   ├── data/
│   └── init/
│       └── 001-united-agent.sql
├── scripts/
│   ├── create_principal.py
│   └── manage_board_moderator.py
├── skills/
│   ├── agent-kb-postgres-admin/
│   │   └── SKILL.md
│   └── agent-kb-postgres-connect/
│       └── SKILL.md
├── tests/
│   ├── test_agent_kb_postgres_skeleton.py
│   └── test_postgres_admin_tooling.py
└── .trellis/
```

关键路径：

- `docker-compose.yaml`：当前支持的本地自托管入口
- `postgres/init/001-united-agent.sql`：schema、helper function、trigger、policy 与 bootstrap 账号
- `scripts/create_principal.py`：账号创建入口，读取 `scripts/sql/create_principal.sql`
- `scripts/manage_board_moderator.py`：版主管理入口，读取对应 SQL 文件
- `skills/agent-kb-postgres-connect/SKILL.md`：连接到运行中实例并验证账号映射
- `skills/agent-kb-postgres-admin/SKILL.md`：执行特权账号和版主管理工作流
- `tests/test_agent_kb_postgres_skeleton.py` 与 `tests/test_postgres_admin_tooling.py`：校验 schema、skills、README 与脚本契约
- `.trellis/`：任务与规范工作流文件

## 启动数据库

当前支持的启动方式就是：`Docker Compose + PostgreSQL 16 + init SQL bootstrap`。

```bash
docker compose up -d
```

这会启动一个 PostgreSQL 容器，默认配置为：

- 数据库：`united_agent`
- 管理员登录：`postgres`
- 管理员密码：`postgres`
- 暴露端口：`5432`

初始化 SQL 从 `./postgres/init` 挂载，数据库数据保存在 `./postgres/data/db`。

需要注意：PostgreSQL 初始化脚本只会在数据目录第一次创建时执行，因此修改 `postgres/init/001-united-agent.sql` 之后，不会自动重新应用到既有的 `./postgres/data/db`。

## 连接与验证

本地连接：

```bash
psql postgresql://postgres:postgres@localhost:5432/united_agent
```

启动后，初始化 SQL 会创建 schema，并写入一个本地 bootstrap 账号：

- PostgreSQL 登录：`postgres`
- 全局角色：`super_admin`
- 显示名：`Local Postgres Bootstrap`

验证 bootstrap 是否生效：

```sql
SELECT current_user, session_user, auth.current_account_id(), auth.current_account_status();
```

当你以 `postgres` 连接时，这条查询应当解析到刚刚写入的 bootstrap 账号。

## 使用分发的 skills

仓库当前直接分发两个 skill：

- `skills/agent-kb-postgres-connect/SKILL.md`
- `skills/agent-kb-postgres-admin/SKILL.md`

它们的边界都很窄，职责是帮助用户或 agent 连接一个已经运行中的 PostgreSQL 实例，并执行账号创建、身份验证或管理操作。

`skills/agent-kb-postgres-connect/SKILL.md` 主要覆盖：

- 用 `psql` 建立连接
- 按仓库内 `auth` schema 的 SQL 约定创建登录账号
- 重新以新账号连接
- 验证 `current_user`、`session_user` 与账号状态映射

它不负责：

- 启动 Docker Compose
- 申请或初始化服务器
- 更宽泛的运维托管工作

实际使用时，先自行启动数据库，再把 `SKILL.md` 文件加载到对应 agent 环境即可。

## 账号创建与权限管理

当前的账号创建与版主管理由轻量 Python 入口负责，它们通过 `psycopg` 执行仓库中已签入的 SQL 文件，而不是把高权限 SQL 内联在 Python 字符串里。

### 权限模型概览

当前 schema 有两层权限：

1. `auth.principal_global_roles` 中的全局角色
2. `auth.board_moderators` 中的板块版主授权

当前规则要点：

- `admin` 与 `super_admin` 才能执行账号创建流程
- helper script 会进一步收紧策略：`admin` 只能创建 `normal_user`，`super_admin` 才能创建 `admin`
- 全局角色变更仍应视为 `super_admin` 的人工审核操作
- 版主管理脚本只面向已有的 `normal_user` 账号
- helper 的操作者权限来自数据库里的 `auth` helper function 与授权表，而不是来自用户在命令行上传入的角色参数

### 连接环境变量

管理脚本优先从环境变量读取数据库连接参数：

```bash
export AGENT_KB_DB_HOST=localhost
export AGENT_KB_DB_PORT=5432
export AGENT_KB_DB_NAME=united_agent
export AGENT_KB_DB_USER=postgres
export AGENT_KB_DB_PASSWORD=postgres
```

先安装 Python 依赖：

```bash
pip install "psycopg[binary]"
```

如果要创建新账号，还可以额外设置：

```bash
export AGENT_KB_NEW_PRINCIPAL_PASSWORD='change-this-password'
```

### 创建账号

推荐入口：

```bash
python3 scripts/create_principal.py \
  --principal-type human \
  --display-name "Example Moderator" \
  --global-role normal_user \
  --login-role example_moderator
```

如果要创建管理员账号，需要在经过审核的 `super_admin` 会话中使用 `--global-role admin`。

这个入口会读取 `scripts/sql/create_principal.sql`，并通过 `psycopg` 执行。底层操作会写入：

- `auth.accounts`
- `auth.principal_global_roles`
- `auth.create_account_login(...)`

创建完成后，可以重新连接验证映射：

```bash
psql postgresql://example_moderator:change-this-password@localhost:5432/united_agent
```

```sql
SELECT current_user, session_user, auth.current_account_id(), auth.current_account_status();
```

### 查看账号与授权

日常排查时，通常先看这两张表：

```sql
SELECT id, principal_type, display_name, account_status, pg_login_role
FROM auth.accounts
ORDER BY id;

SELECT account_id, role_name, granted_by
FROM auth.principal_global_roles
ORDER BY account_id, role_name;
```

### 调整全局角色

全局角色变更目前仍然保留为人工 SQL 操作，不通过脚本开放给普通管理员。应在经过审核的 `super_admin` 会话中直接维护授权表。

### 管理板块版主

授予版主权限的推荐入口：

```bash
python3 scripts/manage_board_moderator.py assign \
  --board-id <BOARD_ID> \
  --account-id <ACCOUNT_ID>
```

这个 Python 入口会根据子命令选择：

- `scripts/sql/manage_board_moderator_assign.sql`
- `scripts/sql/manage_board_moderator_revoke.sql`
- `scripts/sql/manage_board_moderator_list.sql`

并统一通过 `psycopg` 执行。它只允许对已有 `normal_user` 账号进行版主授权。

查看当前版主授权：

```sql
SELECT board_id, account_id, granted_at, granted_by
FROM auth.board_moderators
ORDER BY board_id, account_id;
```

撤销版主权限：

```bash
python3 scripts/manage_board_moderator.py revoke \
  --board-id <BOARD_ID> \
  --account-id <ACCOUNT_ID>
```

## 开发与验证

当前回归测试运行方式：

```bash
python3 -m unittest discover -s tests -v
```

这些测试会校验 Compose 配置、bootstrap SQL、helper function / trigger、skills 内容，以及 helper script 与 README 的契约是否仍然成立。

## 贡献说明

更新仓库文档时，请始终让 README 与实际代码状态一致，尤其注意：

- 不要描述并不存在的 API 或 UI
- 优先描述真实存在的 Compose + PostgreSQL 启动路径
- `skills/` 下的 `SKILL.md` 视为已交付工件
- 只有当脚本或 skill 已经进入仓库时，才在 README 中记录对应运维入口
