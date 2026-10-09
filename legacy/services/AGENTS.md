# Services
- `agent_server/`: Agent后端
- `api_server/`: 业务API
- `sandbox/`: 沙箱镜像构建与发布（工具链 + Phaser skills + 工程骨架烘焙进 `game-runner` 镜像）
- `.env`: 唯一本地配置源
- `docker-compose-local.yml`: 本地编排
- `deploy/`: 仅生产(`docker-compose.yml`+`.env.example`)

## 规则

- 配置全读环境变量,禁写死,无默认值,缺失fail-fast
- 本地改必同步生产:`.env`→`deploy/.env.example`,`docker-compose-local.yml`→`deploy/docker-compose.yml`
- Python 版本由各服务目录自己的 `.python-version` 固定（当前均 `3.14.4`，三份必须保持一致）；三服务 `requires-python` 同样必须一致为 `>=3.14,<3.15`，不再另写 pin
- 跨服务契约（改动必须同步，见 `api_server/app/core/constants.py`、`agent_server/agent/core/constants.py`、`sandbox/build.py`）：
  - 沙箱命名 `game-{thread_id}`、标签 `aigame-thread`
  - 镜像名 `game-runner` + 环境变量 `MODAL_IMAGE_TAG`
  - 沙箱内路径：`/workspace/{work,input}`、`/skills`、`/opt/deps`
  - 发布接口 `POST /api/v1/internal/games/single/publish`；产物 key `games/{thread_id}/index.html`
- 沙箱资产（Phaser skills、工程骨架）只放 `sandbox/assets/`；运行期由 api_server 以命名镜像引用，不做运行时同步
- 沙箱内目录架构见 `sandbox/build.py` 顶部注释；变更须与两服务常量同步
- TODO(多人模式)：沙箱镜像暂不分单/多人（线程不带模式，建沙箱时无从区分）；分模式的前置与两条备选方案见 `sandbox/build.py` 顶部注释
