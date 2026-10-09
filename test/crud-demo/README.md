# CRUD Demo（学习用）

用最小项目练手 **PostgreSQL + REST HTTP + 前后端分离**，并顺带演示当前架构（A1）里的
**「每游戏一个 schema + 专属 role」隔离**。

> 这是学习产物，放在 `test/` 下，不属于正式项目结构。正式架构见 `docs/spec/技术架构规格.md`。

## 一眼看懂的数据流

```
浏览器（Vue, 5173）
   │  HTTP + JSON（fetch）
   ▼
后端（FastAPI, 8000）          ← 这里写 SQL
   │  PostgreSQL 协议
   ▼
数据库（Postgres, 5432）        ← 表 / 约束 / 权限
```

- **REST**：用 HTTP 方法表达操作——`GET` 查、`POST` 增、`PATCH` 改、`DELETE` 删。
- **CRUD**：Create / Read / Update / Delete，就是上面四个动作。
- **为什么要后端**：数据库不该直接暴露给浏览器；凭证、校验、权限都放在后端。

## 目录

```
test/crud-demo/
├── docker-compose.yml        # 用 Docker 起一个本地 Postgres
├── db/init.sql               # 建表 + 初始数据 + schema/role 隔离演示
├── backend/                  # FastAPI（Python）
│   ├── pyproject.toml        # 依赖（uv 管理）
│   └── app/
│       ├── db.py             # 数据库连接池
│       └── main.py           # 4 个 REST 端点，每个对应一条 SQL
└── frontend/                 # Vue（Vite）
    ├── vite.config.js        # 把 /api 代理到后端
    └── src/
        ├── api.js            # 封装 4 个 REST 调用
        └── App.vue           # 界面
```

## 运行（三个终端）

### 1) 数据库

```bash
cd test/crud-demo
docker compose up -d
docker compose ps          # 等它变成 healthy

# 首次运行：建表 + 初始数据 + 隔离演示（可重复执行）
docker exec -i crud-demo-db psql -U postgres -d crud_demo < db/init.sql
```

### 2) 后端（FastAPI）

```bash
cd test/crud-demo/backend
uv run uvicorn app.main:app --reload --port 8000
```

打开 <http://127.0.0.1:8000/docs> —— FastAPI 自动生成的接口文档，可以直接点着调。

### 3) 前端（Vue）

```bash
cd test/crud-demo/frontend
npm install
npm run dev
```

打开 <http://localhost:5173> 即可增删改查。

## 用 curl 直接感受 REST（推荐先做这个）

```bash
# 查（Read）
curl -s http://127.0.0.1:8000/api/todos

# 增（Create）——注意 201 Created
curl -s -X POST http://127.0.0.1:8000/api/todos \
  -H 'Content-Type: application/json' -d '{"title":"用 curl 加一条"}'

# 改（Update）——把 id=1 标记完成
curl -s -X PATCH http://127.0.0.1:8000/api/todos/1 \
  -H 'Content-Type: application/json' -d '{"done":true}'

# 删（Delete）——注意返回 204 No Content
curl -i -X DELETE http://127.0.0.1:8000/api/todos/1
```

## 你在学什么：HTTP ↔ SQL 对照

| REST 请求 | 后端 SQL | 数据库动作 |
|---|---|---|
| `GET /api/todos` | `select ... from public.todos` | 读 |
| `POST /api/todos` | `insert into public.todos ...` | 写 |
| `PATCH /api/todos/{id}` | `update public.todos set ... where id=...` | 改 |
| `DELETE /api/todos/{id}` | `delete from public.todos where id=...` | 删 |

## A1 的数据库隔离模型（本 demo 第 2 课）

当前架构里，**每个游戏一个 schema + 一个专属 role**，游戏服务只能用自己那个 schema。
`db/init.sql` 里已经建好一个演示：

```sql
create schema game_demo;
create role game_demo_rw login password 'demo_pw';
grant usage, create on schema game_demo to game_demo_rw;
alter role game_demo_rw set search_path = game_demo;
revoke all on schema public from game_demo_rw;   -- 关键：拿掉对公共区的访问
```

进容器用这个**受限角色**连一下，感受"只能看到自己 schema"：

```bash
docker exec -it crud-demo-db psql -U game_demo_rw -d crud_demo
# 在 psql 里：
#   create table t(id int);     -- 可以，落在 game_demo
#   \dt public.*                 -- 看不到 public 的表（无权限）
#   select * from public.todos;  -- 报错：permission denied
#   \q
```

对比：用管理员（`-U postgres`）就能看所有 schema。
这就是"最小权限"——每个游戏拿到的连接串只能访问自己那点数据。

> 真实平台里：schema 名由 `game_id` 派生（`game_{sid}`），role 密码由 `HMAC(master_secret, game_id)` 派生，
> 连接串由平台生成并注入游戏服务（见规格 §5.3 / §6.5）。

## 收尾

```bash
cd test/crud-demo
docker compose down          # 停数据库（数据保留在卷里）
docker compose down -v       # 连数据一起删，下次重新初始化
```

## 下一步可以自己练

1. 给 `todos` 加一列 `priority int`，并在前端展示/排序。
2. 加一个 `GET /api/todos/{id}`（单条查询），体会 `404` 的返回。
3. 把 `PATCH` 拆成"只改标题"和"只改状态"两个端点，理解接口设计。
4. 在 `game_demo` schema 里建表、用受限 role 跑 CRUD，体会 A1 的真实形态。
