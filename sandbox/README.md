# 沙盒与游戏模板（sandbox/）

AGS 沙盒资产 + 游戏工程模板的合集；除 `game-template/`（npm 工程）外均为脚本/资产。

| 内容 | 作用 |
|---|---|
| `game-template/` | 游戏工程模板（npm：Express + Socket.IO + Phaser + pg）；建游戏时种入 `games/{game_id}/` |
| `init.sh` | 沙盒初始化：解 skills → `/opt/skills`、装依赖 → `/opt/deps`、软链 `/workspace/work/node_modules`（幂等，api 下发执行） |
| `assets/skills/` | Phaser 技能库（deepagents 经沙盒 backend 读取 `SKILL.md`） |
| `publish_assets.py` | 把 `game-template/`、skills、init.sh 发布到 COS `platform/` 前缀 |

## 发布

```bash
make sandbox-assets-publish
```

发布后 api 的运行期行为：

1. **建游戏**：COS `platform/game-template/**` → `games/{game_id}/`（工作区种入模板）；
2. **进会话（ensure）**：AGS 创建/复用沙盒（`x-mounts.subPath = game_id`）→
   下载 `platform/sandbox/skills.tar.gz` 写入沙盒 `/tmp` → 执行 `platform/sandbox/init.sh`；
3. 确保游戏服务进程运行（`npm run dev`，日志在 `.runtime/server.log`）。

## 注意（坑）

- 挂载前 COS 的 `games/{game_id}/` 与 `input/` 目录必须已存在（api 放 `.keep` 占位）。
- `node_modules` 不放 COS 挂载层（大量小文件性能差）：沙盒初始化时在**沙盒内运行时下载安装**到 `/opt/deps` + 软链；本地依赖一律不上传（模板发布/版本包/部署包均排除）。
- 沙盒内访问挂载点必须 `user="root"`（api/agent 已统一）。
- Tool 级 `StorageMounts` 创建后不可改（需要调整时新建 Tool 并更新 `AGS_TEMPLATE`）。
