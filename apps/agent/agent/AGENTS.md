# agent —— LangGraph Server + deepagents

先应用仓库根 `AGENTS.md`，再应用本文件。

## 职责与信任边界

- 对话编排与工具调用；**只持**沙盒访问权（E2B Key）+ 平台内部令牌 + JWT 公钥（JWKS 本地验签）。
- **禁止**持有任何云管理凭证；管理动作（开通数据库、发布）一律走 api 内部接口。
- 鉴权：`auth.py` 本地验签（`PyJWKClient` 缓存公钥），不引入代验中转（规格 R-AUTH-2）。

## 结构与约定

- `core/`：config / constants（路径与内部接口契约，改动必须与 api、sandbox/image 镜像同步）。
- `infra/`：`ags.py`（连接既有沙盒）、`ags_backend.py`（deepagents `BaseSandbox` 适配）、`model.py`（可配置模型）。
- `tools/`：每个工具一个文件，工厂函数 `make_xxx_tool(...)`；工具返回中文可读字符串，不抛堆栈。
- `prompts/game.py`：系统提示词（生成区边界、素材规则、发布纪律）。
- 沙盒内执行必须 `user="root"`（COS 挂载点权限）。

## 约束（MUST NOT）

- 禁止 `import` 旧实现（`legacy/`）；禁止绕过 api 直接调腾讯云管理 API。
- 内部接口契约以 `apps/api/app/api/schemas/internal.py` 为唯一权威；改动两侧同步并更新根 `AGENTS.md` 接口表。
- 配置全读环境变量（`core/config.py`），缺失 fail-fast，禁写死。
