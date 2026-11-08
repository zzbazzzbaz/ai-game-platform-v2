"""腾讯云 COS 网关（独立桶：工作区 / 素材 / 版本包）。

前缀约定：
- 游戏资产：`games/{game_id}/**`（AGS StorageMount 同一前缀，读写实时互见）
- 版本包：`games/{game_id}/versions/{seq}.tar`
"""

from typing import Any, cast

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

    def input_key(self, game_id: object, asset_id: object, filename: str) -> str:
        """素材 key：每个 asset_id 一个目录，避免同名覆盖。"""
        return f"{self.input_prefix(game_id)}{asset_id}/{filename}"

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
        return self.head_object(key) is not None

    def head_object(self, key: str) -> dict[str, Any] | None:
        """返回对象元数据（Content-Length / Content-Type 等）；不存在返回 None。"""
        try:
            response = self._client.head_object(Bucket=self._bucket, Key=key)
        except CosServiceError as e:
            if e.get_status_code() == 404:
                return None
            raise UpstreamError(f"对象存储查询失败：{key}（{e.get_status_code()}）") from e
        return dict(response)

    def presign_put(self, key: str, *, content_type: str, expires_seconds: int) -> str:
        """签发 PUT 预签名 URL；Content-Type 会签入签名，客户端必须原样发送。"""
        try:
            return cast(
                str,
                self._client.get_presigned_url(
                    Bucket=self._bucket,
                    Key=key,
                    Method="PUT",
                    Expired=expires_seconds,
                    Headers={"Content-Type": content_type},
                ),
            )
        except CosServiceError as e:
            raise UpstreamError(f"预签名生成失败：{key}（{e.get_status_code()}）") from e

    def delete_object(self, key: str) -> None:
        try:
            self._client.delete_object(Bucket=self._bucket, Key=key)
        except CosServiceError as e:
            raise UpstreamError(f"对象存储删除失败：{key}（{e.get_status_code()}）") from e

    def delete_prefix(self, prefix: str) -> int:
        """删除前缀下所有对象；返回删除数量（批量接口单次上限 1000）。"""
        keys = self.list_keys(prefix)
        deleted = 0
        for start in range(0, len(keys), 1000):
            chunk = keys[start : start + 1000]
            try:
                self._client.delete_objects(
                    Bucket=self._bucket,
                    Delete={
                        "Quiet": "true",
                        "Object": [{"Key": key} for key in chunk],
                    },
                )
            except CosServiceError as e:
                raise UpstreamError(f"对象存储批量删除失败：{prefix}（{e.get_status_code()}）") from e
            deleted += len(chunk)
        return deleted

    def list_objects(self, prefix: str) -> list[dict[str, Any]]:
        """列举前缀下对象（含 Size / LastModified），自动翻页。"""
        items: list[dict[str, Any]] = []
        marker = ""
        while True:
            try:
                resp = self._client.list_objects(
                    Bucket=self._bucket, Prefix=prefix, Marker=marker, MaxKeys=1000
                )
            except CosServiceError as e:
                raise UpstreamError(f"对象存储列举失败：{prefix}（{e.get_status_code()}）") from e
            contents = resp.get("Contents") or []
            items.extend(dict(item) for item in contents)
            if resp.get("IsTruncated") != "true":
                return items
            marker = resp.get("NextMarker") or items[-1]["Key"]

    def list_keys(self, prefix: str) -> list[str]:
        return [str(item["Key"]) for item in self.list_objects(prefix)]

    # ---- 业务辅助 ----

    def ensure_game_prefixes(self, game_id: object) -> None:
        """挂载前必须预先存在的目录（放占位对象，坑 #2）。"""
        for key in (
            f"{self.game_prefix(game_id)}.keep",
            f"{self.input_prefix(game_id)}.keep",
        ):
            if not self.exists(key):
                self.put_bytes(key, b"")
