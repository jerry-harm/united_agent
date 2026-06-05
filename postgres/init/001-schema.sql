-- 本地 bootstrap 直接重建受管 schema，确保 postgres/init/*.sql 仍是当前 dev schema 的唯一来源。
DROP SCHEMA IF EXISTS app CASCADE;
DROP SCHEMA IF EXISTS auth CASCADE;

-- 把身份/授权相关表与业务内容表分到不同 schema。
CREATE SCHEMA IF NOT EXISTS auth;
CREATE SCHEMA IF NOT EXISTS app;

-- 锁定 public schema，避免应用角色绕过 auth/app 显式管理对象。
REVOKE ALL ON SCHEMA public FROM PUBLIC;

-- bootstrap / admin 流程为每个应用登录共享的运行时角色；具体登录从它继承表与函数权限。
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'united_agent_user') THEN
    CREATE ROLE united_agent_user NOLOGIN;
  END IF;
END
$$;

-- MVP 核心枚举类型：身份、category、review 状态机直接落在 PostgreSQL。
CREATE TYPE auth.principal_type AS ENUM ('human', 'agent');
CREATE TYPE auth.global_role AS ENUM ('super_admin', 'admin', 'normal_user');
CREATE TYPE auth.account_status AS ENUM ('active', 'disabled');
CREATE TYPE app.category_type AS ENUM ('discussion', 'announcement');
CREATE TYPE app.verification_state AS ENUM ('progressing', 'verified', 'rejected');
