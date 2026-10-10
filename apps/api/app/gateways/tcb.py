"""CloudBase 云托管（CloudRun）部署网关：发布出去的游戏服务。

调用链与 `@cloudbase/manager-node` 的 `cloudrun.deploy()` 等价（已实测）：
  1. tcb:DescribeCloudBaseBuildService → UploadUrl / PackageName / PackageVersion
  2. PUT 源码 zip 到 UploadUrl
  3. tcbr:CreateCloudRunServer / UpdateCloudRunServer（package 模式 + Items）
  4. tcbr:DescribeCloudRunServerDetail → BaseInfo.DefaultDomainName / Status

坑：
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
    TCB_HEALTH_INTERVAL_SECONDS,
    TCB_HEALTH_RETRY_COUNT,
    TCB_READY_INTERVAL_SECONDS,
    TCB_READY_TIMEOUT_SECONDS,
    TCB_UPLOAD_TIMEOUT_SECONDS,
)
from app.core.exceptions import UpstreamError


def _req(cls, **kwargs):
    request = cls()
    for key, value in kwargs.items():
        setattr(request, key, value)
    return request


def normalize_base_url(domain: str) -> str:
    """DefaultDomainName 自带 https:// 前缀；这里统一成绝对 base URL（防止拼出 https://https://）。"""
    cleaned = domain.strip().rstrip("/")
    if not cleaned.startswith(("http://", "https://")):
        cleaned = f"https://{cleaned}"
    return cleaned


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
    ) -> dict:
        """上传源码包并创建/更新 CloudRun 服务（容器型 + Dockerfile）。

        返回部署包信息（含 PackageVersion，可作为版本标识）。
        注意：部署进行中再次提交会 ResourceInUse，内部已轮询重试（实测坑）。
        """
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
                break
            except Exception as e:
                message = str(e)
                if "ResourceInUse" in message or "运行中" in message:
                    time.sleep(TCB_BUSY_RETRY_INTERVAL_SECONDS)
                    continue
                raise UpstreamError(f"云托管部署失败：{message[:300]}") from e
        else:
            raise UpstreamError("云托管部署失败：已有部署任务持续运行中（重试超限）")

        return {
            "package_name": build.PackageName,
            "package_version": build.PackageVersion,
        }

    def _deploy_records(self, *, server_name: str) -> list:
        from tencentcloud.tcbr.v20220217 import models as tcbr_models

        _, tcbr = self._get_clients()
        try:
            rec = tcbr.DescribeCloudRunDeployRecord(
                _req(
                    tcbr_models.DescribeCloudRunDeployRecordRequest,
                    EnvId=self._env_id,
                    ServerName=server_name,
                )
            )
        except Exception:
            return []
        return list(rec.DeployRecords or [])

    def get_latest_deploy_time(self, *, server_name: str) -> str | None:
        """最新一条部署记录的时间（用于判断"是否出现了新部署"）。

        注意：DeployRecords 不保证按时间排序（实测），必须自己取时间最大者。
        """
        records = self._deploy_records(server_name=server_name)
        times = [str(getattr(r, "DeployTime", "")) for r in records]
        return max(times, default=None)

    def _latest_deploy_finished(
        self, *, server_name: str, previous_deploy_time: str | None
    ) -> bool:
        """最新（时间最大）一条部署记录是否为本轮新出现且已完成（status=normal 且 flow>=100）。"""
        records = self._deploy_records(server_name=server_name)
        if not records:
            return False
        latest = max(records, key=lambda r: str(getattr(r, "DeployTime", "")))
        latest_time = str(getattr(latest, "DeployTime", ""))
        if previous_deploy_time is not None and latest_time == previous_deploy_time:
            return False
        status = str(getattr(latest, "Status", "")).lower()
        flow = str(getattr(latest, "FlowRatio", "")).strip()
        flow_ok = flow in ("", "100", "100.0")
        if not flow_ok:
            try:
                flow_ok = float(flow) >= 100
            except ValueError:
                flow_ok = False
        return status == "normal" and flow_ok

    def wait_ready(self, *, server_name: str, previous_deploy_time: str | None = None) -> str:
        """轮询直到默认域名就绪且**本轮**部署记录完成，返回**绝对 base URL**。

        只等 BaseInfo.status 会在镜像构建完成前过早返回（实测坑），必须同时看部署记录；
        更新已有服务时还要排除"上一次已完成记录"，用时间戳判断是否出现新记录。
        """
        deadline = time.time() + TCB_READY_TIMEOUT_SECONDS
        last_status = "未知"
        while time.time() < deadline:
            detail = self.get_server_detail(server_name=server_name)
            if detail:
                domain = detail.get("default_domain")
                status = detail.get("status")
                last_status = str(status)
                if (
                    domain
                    and status in (None, "", "running", "normal", "RUNNING", "NORMAL", "online")
                    and self._latest_deploy_finished(
                        server_name=server_name, previous_deploy_time=previous_deploy_time
                    )
                ):
                    return normalize_base_url(domain)
            time.sleep(TCB_READY_INTERVAL_SECONDS)
        raise UpstreamError(f"等待云托管就绪超时（最后状态：{last_status}）")

    def probe_health(self, base_url: str) -> None:
        """就绪后探测 /api/health（含冷启动重试）。base_url 为绝对地址。"""
        url = f"{base_url.rstrip('/')}/api/health"
        for _attempt in range(TCB_HEALTH_RETRY_COUNT):
            try:
                resp = httpx.get(url, timeout=20)
                if resp.status_code == 200:
                    return
            except httpx.HTTPError:
                pass
            time.sleep(TCB_HEALTH_INTERVAL_SECONDS)
        raise UpstreamError("部署完成但健康检查未通过（/api/health）")

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
