# apps/frontent-test-1 —— 平台前端（React SPA）

面向无编程基础用户：登录 → 选游戏 → 与 AI 对话生成 → 沙盒内预览试玩 → 发布。

技术栈：Vite + React 19 + TypeScript + Tailwind CSS v4（shadcn/ui）+ react-router + TanStack Query + `@langchain/langgraph-sdk`。

## 运行

```bash
npm install
npm run dev     # http://localhost:5173
npm run build   # 产物 dist/（由 Nginx 静态托管）
npm run lint
```

本地配置**唯一来源为 `apps/.env`**（Vite `envDir` 指到上一级目录），需要 api 与 LangGraph Server 同时启动（见仓库根 `Makefile`）。

## 环境变量（apps/.env 的 frontend 组）

| 变量 | 说明 |
|---|---|
| `VITE_API_BASE_URL` | 平台后端基路径（默认 `/api/v1`） |
| `VITE_LG_BASE_URL` | LangGraph Server 基路径（默认 `/lg`） |
| `VITE_LG_ASSISTANT_ID` | 图 ID（`game`） |
| `VITE_API_PROXY_TARGET` | 开发代理目标：api（`http://127.0.0.1:8000`） |
| `VITE_LG_PROXY_TARGET` | 开发代理目标：LangGraph（`http://127.0.0.1:2024`） |

开发态由 Vite 代理、生产态由 Nginx 反代：前端只使用相对路径，两端行为一致，无需 CORS 配置。

## 目录结构

```
src/
├── api/          # 请求层（Bearer 注入 / 401 自动续期 / LangGraph Client）、各域接口
├── auth/         # 登录态上下文与路由守卫
├── components/ui # shadcn 组件（自参考实现移植）
├── features/
│   ├── auth/     # 登录注册页
│   ├── games/    # 游戏列表与新建
│   ├── workbench/# 工作台：顶栏、会话栏、预览面板、版本抽屉
│   └── chat/     # 对话流：消息渲染、工具调用卡片、Markdown
├── lib/          # 运行期配置、格式化、工具函数
├── routes/       # 布局与 404
└── theme/        # 深色/浅色主题
```

## 与后端的两条约定

1. **会话先由 api 创建**：`POST /api/v1/games/{game_id}/threads` 返回 `thread_id`，agent 的 `ensure` 依赖该映射；前端随后用**同一个 UUID** 在 LangGraph 侧补建线程（`POST /lg/threads`，`if_exists=do_nothing`，幂等），再开始对话。
2. **鉴权同一套 JWT**：两个后端都用平台 access_token（Bearer）；token 过期前 60 秒自动续期一次，续期失败回登录页。

## 已实现范围

- 登录 / 注册、401 自动续期、登出
- 游戏列表、新建游戏、（列表按最后活动时间排序）
- 工作台：会话栏（列表/新建）、流式对话（工具调用卡片、停止、错误重发）、
  点击加载的 NoVNC 预览（适应窗口/原始比例、全屏、刷新）、版本抽屉
- 深色/浅色主题、基础响应式
