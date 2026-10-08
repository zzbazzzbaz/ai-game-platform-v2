# M4b 验证结论：自建 VPS PostgreSQL（开通 + 沙盒直连）

- 日期：2026-10-08
- 范围：`152.32.215.89:10050`（用户提供的 VPS PostgreSQL）——建库/建角色能力、沙盒直连、隔离、SSL
- 结论：**全部可行，但有 2 个必须处理项**（SSL 未启用、`PUBLIC` 默认 CONNECT 的越库坑）
- 验证脚本：`test/infra/sandbox/m4b_vps_pg_verify.py`

## 一、服务器现状（实测）

| 项 | 值 |
|---|---|
| 版本 | PostgreSQL **17.11**（Debian 17.11-1.pgdg13+2） |
| 连接地址 | 公网 `152.32.215.89:10050` → 内网 `172.19.0.2:5432`（Docker 端口映射） |
| `root` 权限 | **SUPERUSER + CREATEDB + CREATEROLE + LOGIN** ✅ |
| **SSL** | ❌ **`ssl = off`（未启用）** |
| 现有库 | `postgres`、`docx-check`、`docx-check_test`、`postgres_test`（共享实例，与平台无关） |

## 二、开通与隔离（平台侧，实测）

| 验证项 | 结果 |
|---|---|
| `CREATE DATABASE`（psycopg） | ✅ ~96ms |
| `CREATE DATABASE`（asyncpg，后端实际驱动） | ✅ |
| `CREATE ROLE ... LOGIN PASSWORD` | ✅ |
| `GRANT CONNECT` + 库内授权 | ✅ |
| 游戏 role 连接**自己的库**并建表/写入 | ✅ |
| 游戏 role 连接**别的游戏库** | 默认 ❌（可连，越库！）→ **`REVOKE CONNECT ... FROM PUBLIC` 后被拒** ✅ |

> **关键坑（默认隔离失效）**：PostgreSQL 建库时 `PUBLIC` 默认持有 `CONNECT`，因此**任意 role 都能连接任意库**。
> 开通游戏库必须显式执行：
> ```sql
> REVOKE CONNECT ON DATABASE game_{sid} FROM PUBLIC;
> GRANT CONNECT ON DATABASE game_{sid} TO game_{sid}_rw;
> ```
> 平台自身库（平台元数据）同样要 `REVOKE CONNECT ... FROM PUBLIC`，否则游戏 role 可连平台库（可读到 `pg_stat_activity` 等）。
> 另：本测试在共享实例上操作，**`postgres` 库 ACL 已恢复原状**（`{=Tc/root,root=CTc/root}`）。

## 三、AGS 沙盒 → VPS PG（实测）

| 验证项 | 结果 |
|---|---|
| 沙盒内 TCP `152.32.215.89:10050` | ✅ **OPEN** |
| 沙盒内用游戏 role 连接（`sslmode=disable`） | ✅ `current_user=game_m4b_probe_rw`、`inet_server_addr=172.19.0.2` |
| 沙盒内建表 + 写入 + 计数 | ✅ |
| 往返耗时 | ✅ 整个探针（连接+DDL+写入+查询）**0.6s** |
| `sslmode=require` | ❌ `server does not support SSL, but SSL was required` |

> **结论**：沙盒（开发态）可**公网直连** VPS PG，不需要 VPC；但当前是**明文传输**（含数据库密码）。发布态（云托管）同样已验证公网直连（见 `test/M6b-API部署与连库验证结论.md`）。

## 四、必须处理项（对规格的影响）

1. **启用 SSL**（对应规格 Q1/Q8）：
   - 最小改动：PG 配**自签证书**，客户端 `sslmode=require`（不校验证书链，仅加密）——足以消除明文风险；
   - 更严：正式证书 + `sslmode=verify-full`；
   - 备选：跳板/隧道（stunnel、SSH 隧道），但复杂且沙盒内不易维护。
   - ⚠️ 现状下 `root` 密码在公网明文传输，建议**尽快**处理（并注意该密码已出现在对话中）。
2. **开通流程必须含 `REVOKE CONNECT ... FROM PUBLIC`**（见上），并写入规格的 `provision_database()` 伪码与验收。
3. 共享实例注意：平台库/游戏库与用户其它业务（`docx-check`）**同实例**；互不影响的前提是上述 CONNECT 收敛 + 各自 role 最小权限。

## 五、对规格的建议改动（待决策后落笔）

- 规格 §5/§6 的隔离单位二选一：
  - **A. database-per-game（本次实测口径，推荐）**：`game_{sid}` 库 + `game_{sid}_rw` role；跨库天然不可见（收 CONNECT 后），隔离最强、`REVOKE` 后无目录级泄漏；
  - **B. schema-per-game（现行规格）**：单库多 schema；需额外 `REVOKE` 其它 schema 的 `USAGE` 并管理 `search_path`，且同库目录（`pg_class`）会暴露其它游戏的表名。
- M4 里程碑验收从"沙盒 SSL 直连"改为"沙盒**加密**直连"（先启用 SSL）。

## 六、复现

```bash
cd test/infra/sandbox
set -a; source .env; set +a
VPS_PG_PASSWORD=*** uv run --with e2b --with "psycopg[binary]" python m4b_vps_pg_verify.py
```

沙盒内装依赖（网络慢时用腾讯云镜像）：
```bash
python3 -m pip install --user -i https://mirrors.cloud.tencent.com/pypi/simple psycopg2-binary
```
