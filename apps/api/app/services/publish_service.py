"""发布（M6 接入）。

目标流程（规格 §7.1，API 链路已在 test/infra/cloudbase 实测）：
  1. 校验工作区可构建、监听端口、`/api/health` 正常、无绝对域名/端口
  2. 打包工作区 → COS `games/{game_id}/versions/{seq}.tar`
  3. `TcbGateway.deploy_package`（注入 DATABASE_URL / PORT / NODE_ENV）部署 `game-{game_id}`
  4. 写 `game_versions`（seq + revision + deployed）并更新 `games.public_url`

当前骨架阶段未接入；M6 按上述步骤实现。
"""

import uuid

from sqlalchemy.orm import Session

from app.core.exceptions import UpstreamError


def publish_game(*, thread_id: uuid.UUID, name: str, session: Session, **deps) -> dict:
    raise UpstreamError("发布链路尚未接入（M6 实现：打包 → COS 版本包 → CloudRun 部署 → 版本落库）")
