# 数据库拓扑（开发阶段）

## 两类数据库

| 库 | 位置 | 内容 | 谁维护 |
|---|---|---|---|
| 平台元数据库 `aigame_platform`（schema `platform`） | **本地 Docker PG**（`docker-compose.yml`） | `users` / `games` / `game_threads` / `game_versions` | `apps/api`（启动时 `CREATE SCHEMA` + `create_all`） |
| 游戏数据库 `game_{sid}` + role `game_{sid}_rw` | **公网 VPS PG**（`152.32.215.89:10050`） | 每个游戏自己的表（由游戏工程 `db/migrate.js` 建） | `apps/api` 管理员凭证**幂等**开通 |

> `sid = game_id 去掉 "-"`（32 位十六进制）。
> 平台库与游戏库**不在同一实例**（开发阶段），隔离规则不变。

## 游戏库开通（api 代码：`app/gateways/pg_admin.py`）

幂等语义（规格 §6.5，实测结论见 `docs/chat/10.8/03-验证结论与坑.md` §3）：

```sql
-- 仅当不存在时执行（不重建、不改密码）
CREATE DATABASE game_{sid};
REVOKE CONNECT ON DATABASE game_{sid} FROM PUBLIC;   -- 关键：否则任意 role 可连任意库
CREATE ROLE game_{sid}_rw LOGIN PASSWORD '<base64url(HMAC-SHA256(master_secret, game_id))>';
GRANT CONNECT ON DATABASE game_{sid} TO game_{sid}_rw;
-- 连入 game_{sid} 后：
GRANT USAGE, CREATE ON SCHEMA public TO game_{sid}_rw;
```

注入游戏的连接串（派生，不落库）：

```
postgresql://game_{sid}_rw:<pwd>@152.32.215.89:10050/game_{sid}?sslmode=disable
```

> ⚠️ 当前 VPS PG `ssl=off`（明文），上线前必须启用 SSL 并改 `sslmode=require`（规格 Q1/Q8）。

## 本地平台库重置

```bash
docker compose down -v && docker compose up -d   # 清空本地平台库
# api 下次启动会重新建 schema 与表
```
