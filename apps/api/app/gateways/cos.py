"""腾讯云 COS 网关（独立桶：工作区 / 素材 / 版本包 / 平台资产）。

前缀约定：
- 游戏资产：`games/{game_id}/**`（AGS StorageMount 同一前缀，读写实时互见）
- 版本包：`games/{game_id}/versions/{seq}.tar`
- 平台资产：`platform/**`（由 sandbox/publish_assets.py 发布）
"""

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
        platform_prefix: str,
    ) -> None:
        config = CosConfig(
            Region=region, SecretId=secret_id, SecretKey=secret_key, Scheme="https"
        )
        self._client = CosS3Client(config)
        self._bucket = bucket
        self._games_prefix = games_prefix.strip("/")
        self._platform_prefix = platform_prefix.strip("/")

    # ---- 前缀派生 ----

    def game_prefix(self, game_id: object) -> str:
        return f"{self._games_prefix}/{game_id}/"

    def input_prefix(self, game_id: object) -> str:
        return f"{self.game_prefix(game_id)}input/"

    def work_key(self, game_id: object, rel_path: str) -> str:
        return f"{self.game_prefix(game_id)}{rel_path}"

    def version_key(self, game_id: object, seq: int) -> str:
        return f"{self.game_prefix(game_id)}versions/{seq}.tar"

    def platform_key(self, rel_path: str) -> str:
        return f"{self._platform_prefix}/{rel_path}"

    # ---- 基础读写 ----

    def put_bytes(self, key: str, data: bytes, content_type: str = _BINARY) -> None:
        try:
            self._client.put_object(Bucket=self._bucket, Key=key, Body=data, ContentType=content_type)
        except CosServiceError as e:
            raise UpstreamError(f"对象存储写入失败：{key}（{e.get_status_code()}）") from e

    def get_bytes(self, key: str) -> bytes | None:
        try:
            resp = self._client.get_object(Bucket=self._bucket, Key=key)
        except CosServiceError as e:
            if e.get_status_code() == 404:
                return None
            raise UpstreamError(f"对象存储读取失败：{key}（{e.get_status_code()}）") from e
        return resp["Body"].get_raw_stream().read()

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

    def copy_object(self, src_key: str, dst_key: str) -> None:
        try:
            self._client.copy_object(
                Bucket=self._bucket,
                Key=dst_key,
                CopySource={"Bucket": self._bucket, "Key": src_key, "Region": self._region_of_client()},
            )
        except CosServiceError as e:
            raise UpstreamError(f"对象存储复制失败：{src_key} → {dst_key}") from e

    def _region_of_client(self) -> str:
        return self._client._conf._region  # SDK 未暴露公开属性

    def copy_prefix(self, src_prefix: str, dst_prefix: str) -> int:
        count = 0
        for key in self.list_keys(src_prefix):
            rel = key[len(src_prefix) :].lstrip("/")
            self.copy_object(key, f"{dst_prefix.rstrip('/')}/{rel}")
            count += 1
        return count

    # ---- 业务辅助 ----

    def ensure_game_prefixes(self, game_id: object) -> None:
        """挂载前必须预先存在的目录（放占位对象，坑 #2）。"""
        for key in (
            f"{self.game_prefix(game_id)}.keep",
            f"{self.input_prefix(game_id)}.keep",
        ):
            if not self.exists(key):
                self.put_bytes(key, b"")

    def seed_workspace(self, game_id: object) -> int:
        """工作区为空时，从平台模板前缀种入初始工程；返回复制文件数。"""
        marker = self.work_key(game_id, "package.json")
        if self.exists(marker):
            return 0
        return self.copy_prefix(
            f"{self.platform_key('game-template').rstrip('/')}/", self.game_prefix(game_id)
        )
