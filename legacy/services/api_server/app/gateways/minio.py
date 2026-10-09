from datetime import UTC, datetime

import boto3
from botocore.config import Config as BotoConfig
from botocore.exceptions import ClientError

from app.core.constants import WORK_INDEX_FILE
from app.core.exceptions import UpstreamError


def work_prefix(thread_id: str) -> str:
    return f"threads/{thread_id}/work/"


def work_key(thread_id: str, rel_path: str) -> str:
    return f"threads/{thread_id}/work/{rel_path}"


def manifest_key(thread_id: str) -> str:
    return f"threads/{thread_id}/work/manifest.json"


def input_prefix(thread_id: str) -> str:
    return f"threads/{thread_id}/input/"


def input_key(thread_id: str, filename: str) -> str:
    return f"threads/{thread_id}/input/{filename}"


def game_key(thread_id: str) -> str:
    return f"games/{thread_id}/{WORK_INDEX_FILE}"


def utc_timestamp() -> str:
    return datetime.now(UTC).strftime("%Y%m%d%H%M%S")


class MinioGateway:
    def __init__(
        self,
        *,
        endpoint_url: str,
        bucket: str,
        path_style: bool,
        access_key: str,
        secret_key: str,
    ) -> None:
        self._bucket = bucket
        self._client = boto3.client(
            "s3",
            endpoint_url=endpoint_url,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name="us-east-1",
            config=BotoConfig(s3={"addressing_style": "path" if path_style else "auto"}),
        )

    def ensure_bucket(self) -> None:
        try:
            self._client.head_bucket(Bucket=self._bucket)
        except ClientError as e:
            code = e.response.get("Error", {}).get("Code", "")
            if code not in ("404", "NoSuchBucket", "NotFound"):
                raise UpstreamError(f"对象存储不可用：{code or e}") from e
            self._client.create_bucket(Bucket=self._bucket)

    def put_bytes(self, key: str, data: bytes, content_type: str) -> None:
        try:
            self._client.put_object(
                Bucket=self._bucket, Key=key, Body=data, ContentType=content_type
            )
        except ClientError as e:
            raise UpstreamError(f"对象存储写入失败：{key}") from e

    def put_bytes_if_absent(self, key: str, data: bytes, content_type: str) -> bool:
        try:
            self._client.put_object(
                Bucket=self._bucket,
                Key=key,
                Body=data,
                ContentType=content_type,
                IfNoneMatch="*",
            )
            return True
        except ClientError as e:
            if e.response.get("Error", {}).get("Code") == "PreconditionFailed":
                return False
            raise UpstreamError(f"对象存储写入失败：{key}") from e

    def put_file(self, key: str, local_path: str, content_type: str) -> None:
        try:
            with open(local_path, "rb") as handle:
                self._client.put_object(
                    Bucket=self._bucket, Key=key, Body=handle, ContentType=content_type
                )
        except ClientError as e:
            raise UpstreamError(f"对象存储写入失败：{key}") from e

    def get_bytes(self, key: str) -> bytes | None:
        try:
            resp = self._client.get_object(Bucket=self._bucket, Key=key)
            return resp["Body"].read()
        except ClientError as e:
            if e.response.get("Error", {}).get("Code") in ("NoSuchKey", "404", "NotFound"):
                return None
            raise UpstreamError(f"对象存储读取失败：{key}") from e

    def open_stream(self, key: str):
        try:
            return self._client.get_object(Bucket=self._bucket, Key=key)["Body"]
        except ClientError as e:
            if e.response.get("Error", {}).get("Code") in ("NoSuchKey", "404", "NotFound"):
                return None
            raise UpstreamError(f"对象存储读取失败：{key}") from e

    def list_keys(self, prefix: str) -> list[dict]:
        keys, token = [], None
        while True:
            kwargs = {"Bucket": self._bucket, "Prefix": prefix}
            if token:
                kwargs["ContinuationToken"] = token
            try:
                resp = self._client.list_objects_v2(**kwargs)
            except ClientError as e:
                raise UpstreamError(f"对象存储列举失败：{prefix}") from e
            for item in resp.get("Contents", ()):
                keys.append({"key": item["Key"], "size": item["Size"]})
            token = resp.get("NextContinuationToken")
            if not token:
                return keys

    def delete_keys(self, keys: list[str]) -> None:
        for i in range(0, len(keys), 1000):
            chunk = keys[i : i + 1000]
            try:
                self._client.delete_objects(
                    Bucket=self._bucket, Delete={"Objects": [{"Key": k} for k in chunk]}
                )
            except ClientError as e:
                raise UpstreamError("对象存储删除失败") from e
