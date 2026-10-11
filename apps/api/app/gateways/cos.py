"""腾讯云 COS 网关（独立桶：工作区 / 素材 / 版本包）。

前缀约定：
- 游戏资产：`games/{game_id}/**`（AGS StorageMount 同一前缀，读写实时互见）
- 版本包：`games/{game_id}/versions/{seq}.tar`
"""

from typing import cast

from qcloud_cos import CosConfig, CosS3Client
from qcloud_cos.cos_exception import CosServiceError

from app.core.exceptions import UpstreamError

_BINARY = "application/octet-stream"


class CosGateway:
    def __init__(
        self,
        *,
        secret_id: str,
        secret_key: str,
        region: str,
        bucket: str,
        games_prefix: str,
    ) -> None:
        config = CosConfig(Region=region, SecretId=secret_id, SecretKey=secret_key, Scheme="https")
        self._client = CosS3Client(config)
        self._bucket = bucket
        self._games_prefix = games_prefix.strip("/")

    # ---- 前缀派生 ----

    def game_prefix(self, game_id: object) -> str:
        return f"{self._games_prefix}/{game_id}/"

    def input_prefix(self, game_id: object) -> str:
        return f"{self.game_prefix(game_id)}input/"

    def version_key(self, game_id: object, seq: int) -> str:
        return f"{self.game_prefix(game_id)}versions/{seq}.tar"

    # ---- 基础读写 ----

    def put_bytes(self, key: str, data: bytes, content_type: str = _BINARY) -> None:
        try:
            self._client.put_object(
                Bucket=self._bucket, Key=key, Body=data, ContentType=content_type
            )
        except CosServiceError as e:
            raise UpstreamError(f"对象存储写入失败：{key}（{e.get_status_code()}）") from e

    def get_bytes(self, key: str) -> bytes | None:
        try:
            resp = self._client.get_object(Bucket=self._bucket, Key=key)
        except CosServiceError as e:
            if e.get_status_code() == 404:
                return None
            raise UpstreamError(f"对象存储读取失败：{key}（{e.get_status_code()}）") from e
        return cast(bytes, resp["Body"].get_raw_stream().read())

    def exists(self, key: str) -> bool:
        try:
            self._client.head_object(Bucket=self._bucket, Key=key)
            return True
        except CosServiceError as e:
            if e.get_status_code() == 404:
                return False
            raise UpstreamError(f"对象存储查询失败：{key}（{e.get_status_code()}）") from e

    def list_keys(self, prefix: str) -> list[str]:
        keys: list[str] = []
        marker = ""
        while True:
            try:
                resp = self._client.list_objects(
                    Bucket=self._bucket, Prefix=prefix, Marker=marker, MaxKeys=1000
                )
            except CosServiceError as e:
                raise UpstreamError(f"对象存储列举失败：{prefix}（{e.get_status_code()}）") from e
            for item in resp.get("Contents") or []:
                keys.append(item["Key"])
            if resp.get("IsTruncated") != "true":
                return keys
            marker = resp.get("NextMarker") or keys[-1]

    # ---- 业务辅助 ----

    def ensure_game_prefixes(self, game_id: object) -> None:
        """挂载前必须预先存在的目录（放占位对象，坑 #2）。"""
        for key in (
            f"{self.game_prefix(game_id)}.keep",
            f"{self.input_prefix(game_id)}.keep",
        ):
            if not self.exists(key):
                self.put_bytes(key, b"")
