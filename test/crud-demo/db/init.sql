-- ============================================================
-- 初始化脚本（可重复执行）
-- 用法：
--   docker compose up -d
--   docker exec -i crud-demo-db psql -U postgres -d crud_demo < db/init.sql
-- ============================================================

-- 1) 业务表：待办清单
create table if not exists public.todos (
  id         bigserial primary key,
  title      text        not null,
  done       boolean     not null default false,
  created_at timestamptz not null default now()
);

-- 2) 表为空时撒两条初始数据
insert into public.todos (title, done)
select * from (values
  ('理解 Postgres 的表结构', true),
  ('写一个 CRUD API', false)
) as seed(title, done)
where not exists (select 1 from public.todos);

-- ============================================================
-- 3) 【A1 隔离模型演示】每游戏一个 schema + 专属 role
--    真实平台里，schema 名由 game_id 派生、role 密码由 HMAC 派生；
--    这里用固定的 game_demo / demo_pw 方便学习。
-- ============================================================

create schema if not exists game_demo;

-- 角色不存在才创建（CREATE ROLE 没有 IF NOT EXISTS）
do $$
begin
  if not exists (select 1 from pg_roles where rolname = 'game_demo_rw') then
    create role game_demo_rw login password 'demo_pw';
  end if;
end
$$;

-- 只把这个 schema 的权限给它
grant usage, create on schema game_demo to game_demo_rw;
alter default privileges in schema game_demo
  grant all on tables    to game_demo_rw;
alter default privileges in schema game_demo
  grant all on sequences to game_demo_rw;

-- 固化搜索路径（连上后不写 schema 前缀，也是操作 game_demo）
alter role game_demo_rw set search_path = game_demo;

-- 关键：收回它对 public 的访问（这样它只能碰 game_demo）
revoke all on schema public from game_demo_rw;
