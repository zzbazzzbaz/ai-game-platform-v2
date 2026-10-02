# M1 沙盒链路验证

验证目标（规格 §13 · M1）：**沙盒内跑 Node 游戏服务，沙盒内浏览器打开，外部 CDP 可操作同一浏览器。**

## 前置

1. 在 [AGS 控制台](https://console.cloud.tencent.com/ags/sandbox) 创建：
   - **API Key**（`e2b_` 前缀）
   - **沙箱工具**：类型选 **All-In-One（`aio`）**，网络模式 **`PUBLIC`**，记下**工具名或 ToolId（`sdt-...`）**（两者均可作为 `template`）。`aio` 是预置类型，**无需自定义镜像**；运行时用 `pip/npm install` 装依赖即可。
2. `E2B_DOMAIN` 与工具所在地域一致：
   - 广州 `ap-guangzhou.tencentags.com`
   - 上海 `ap-shanghai.tencentags.com`

## 使用

```bash
cd test/infra/sandbox

# 1) 预检：校验 key/域名，列出运行中沙盒（不需要模板名）
uv run --env-file .env m1_verify.py check

# 2) 完整验证：创建沙盒 → 起占位服务 → CDP 打开并截图 → 打印 NoVNC 地址
uv run --env-file .env m1_verify.py run --keep

# 3) 用浏览器打开脚本打印的 NoVNC 地址，人工确认「可见画面、可操作」
# 4) 验证完销毁
uv run --env-file .env m1_verify.py kill <sandbox_id>
```

`.env` 从 `.env.example` 复制。`.env` 已被 git 忽略，**不要提交**。

## 产出

- `artifacts/m1.png`：CDP 截取的沙盒浏览器画面。
- 终端打印的 `NoVNC` / `CDP` 地址。

## 通过标准

| 检查点 | 期望 |
|---|---|
| `check` | 返回 200，列出沙盒（可为 0） |
| 占位服务 | `/api/ping` 返回 200 |
| CDP | 能导航、标题为 `M1 Placeholder Game`、截图成功 |
| NoVNC | 打开后看到同一画面（绿球动画），可操作 |

## 已知问题

- 本机若开着 Clash 等代理，`*.tencentags.com` 可能被 DNS 劫持到 `0.0.0.0/1` 导致连不通；验证时关闭代理或放行该域名。
