"""CloudBase 云托管（CloudRun）部署网关：发布出去的游戏服务。

调用链与 `@cloudbase/manager-node` 的 `cloudrun.deploy()` 等价，已经
`test/infra/cloudbase/api_deploy_verify.py` 实测（2026-10-08）：
  1. tcb:DescribeCloudBaseBuildService → UploadUrl / PackageName / PackageVersion
  2. PUT 源码 zip 到 UploadUrl
  3. tcbr:CreateCloudRunServer / UpdateCloudRunServer（package 模式 + Items）
  4. tcbr:DescribeCloudRunServerDetail → BaseInfo.DefaultDomainName / Status

坑（见 03-验证结论与坑 §4.4）：
  - 部署中再次提交会 ResourceInUse → 必须轮询重试；
  - 源码构建偶发 broken pipe → 由调用方重试；
  - 端口必须与服务监听一致（容器型显式 Port）。
"""

import json
import time

import httpx

from app.core.constants import (
    TCB_BUSY_RETRY_COUNT,
    TCB_BUSY_RETRY_INTERVAL_SECONDS,
    TCB_UPLOAD_TIMEOUT_SECONDS,
)
from app.core.exceptions import UpstreamError


def _req(cls, **kwargs):
    request = cls()
    for key, value in kwargs.items():
        setattr(request, key, value)
    return request


class TcbGateway:
    def __init__(self, *, secret_id: str, secret_key: str, env_id: str, region: str) -> None:
        self._secret_id = secret_id
        self._secret_key = secret_key
        self._env_id = env_id
        self._region = region
        self._clients = None

    def _get_clients(self):
        if self._clients is None:
            from tencentcloud.common import credential
            from tencentcloud.common.profile.client_profile import ClientProfile
            from tencentcloud.common.profile.http_profile import HttpProfile
            from tencentcloud.tcb.v20180608 import tcb_client
            from tencentcloud.tcbr.v20220217 import tcbr_client

            cred = credential.Credential(self._secret_id, self._secret_key)
            tcb_profile = ClientProfile(httpProfile=HttpProfile(endpoint="tcb.tencentcloudapi.com"))
            tcbr_profile = ClientProfile(
                httpProfile=HttpProfile(endpoint="tcbr.tencentcloudapi.com")
            )
            self._clients = (
                tcb_client.TcbClient(cred, self._region, tcb_profile),
                tcbr_client.TcbrClient(cred, self._region, tcbr_profile),
            )
        return self._clients

    def deploy_package(
        self,
        *,
        server_name: str,
        zip_bytes: bytes,
        env_params: dict,
        port: int,
    ) -> None:
        """上传源码包并创建/更新 CloudRun 服务（容器型 + Dockerfile）。"""
        from tencentcloud.tcb.v20180608 import models as tcb_models
        from tencentcloud.tcbr.v20220217 import models as tcbr_models

        tcb, tcbr = self._get_clients()
        try:
            build = tcb.DescribeCloudBaseBuildService(
                _req(
                    tcb_models.DescribeCloudBaseBuildServiceRequest,
                    EnvId=self._env_id,
                    ServiceName=server_name,
                )
            )
        except Exception as e:
            raise UpstreamError(f"获取云托管构建服务失败：{e}") from e

        headers = {kv.Key: kv.Value for kv in (build.UploadHeaders or [])}
        try:
            resp = httpx.put(
                build.UploadUrl,
                content=zip_bytes,
                headers=headers,
                timeout=TCB_UPLOAD_TIMEOUT_SECONDS,
            )
            resp.raise_for_status()
        except httpx.HTTPError as e:
            raise UpstreamError(f"源码包上传失败：{e}") from e

        items = [
            _req(tcbr_models.DiffConfigItem, Key="AccessTypes", ArrayValue=["PUBLIC"]),
            _req(tcbr_models.DiffConfigItem, Key="MinNum", IntValue=0),
            _req(
                tcbr_models.DiffConfigItem,
                Key="EnvParam",
                Value=json.dumps(env_params),
            ),
            _req(tcbr_models.DiffConfigItem, Key="InitialDelaySeconds", IntValue=0),
            _req(tcbr_models.DiffConfigItem, Key="HasDockerfile", BoolValue=True),
            _req(tcbr_models.DiffConfigItem, Key="Port", IntValue=port),
            _req(tcbr_models.DiffConfigItem, Key="Dockerfile", Value="Dockerfile"),
        ]
        deploy_info = _req(
            tcbr_models.DeployParam,
            DeployType="package",
            PackageName=build.PackageName,
            PackageVersion=build.PackageVersion,
            ReleaseType="FULL",
        )

        exists = False
        try:
            tcbr.DescribeCloudRunServerDetail(
                _req(
                    tcbr_models.DescribeCloudRunServerDetailRequest,
                    EnvId=self._env_id,
                    ServerName=server_name,
                )
            )
            exists = True
        except Exception:
            exists = False

        def _do_once():
            if exists:
                return tcbr.UpdateCloudRunServer(
                    _req(
                        tcbr_models.UpdateCloudRunServerRequest,
                        EnvId=self._env_id,
                        ServerName=server_name,
                        DeployInfo=deploy_info,
                        Items=items,
                    )
                )
            return tcbr.CreateCloudRunServer(
                _req(
                    tcbr_models.CreateCloudRunServerRequest,
                    EnvId=self._env_id,
                    ServerName=server_name,
                    DeployInfo=deploy_info,
                    Items=items,
                )
            )

        for _attempt in range(TCB_BUSY_RETRY_COUNT):
            try:
                _do_once()
                return
            except Exception as e:
                message = str(e)
                if "ResourceInUse" in message or "运行中" in message:
                    time.sleep(TCB_BUSY_RETRY_INTERVAL_SECONDS)
                    continue
                raise UpstreamError(f"云托管部署失败：{message[:300]}") from e
        raise UpstreamError("云托管部署失败：已有部署任务持续运行中（重试超限）")

    def get_server_detail(self, *, server_name: str) -> dict | None:
        """返回 {default_domain, status}；服务不存在返回 None。"""
        from tencentcloud.tcbr.v20220217 import models as tcbr_models

        _, tcbr = self._get_clients()
        try:
            detail = tcbr.DescribeCloudRunServerDetail(
                _req(
                    tcbr_models.DescribeCloudRunServerDetailRequest,
                    EnvId=self._env_id,
                    ServerName=server_name,
                )
            )
        except Exception:
            return None
        base = getattr(detail, "BaseInfo", None)
        if base is None:
            return None
        return {
            "default_domain": getattr(base, "DefaultDomainName", None),
            "status": getattr(base, "Status", None),
        }
