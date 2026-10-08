#!/usr/bin/env python3
"""验证：后端代码（腾讯云 Python SDK）直接调 API 部署服务到 CloudBase 云托管，并连接自建 VPS PostgreSQL。

流程与 `@cloudbase/manager-node` 的 `cloudrun.deploy()` 完全一致（后端可用 Python 复刻）：
  1. tcb.DescribeCloudBaseBuildService   → 拿上传 URL / PackageName / PackageVersion
  2. PUT 源码 zip 上传到 build service
  3. tcbr.CreateCloudRunServer           → DeployType=package 部署（容器型，Dockerfile）
  4. 轮询 DescribeCloudRunServerDetail    → 等默认域名就绪
  5. 请求 `/` 与 `/db`（服务内通过 DATABASE_URL 连 VPS PG）
  6. 清理（--keep 可保留服务）

用法：
  cd test/infra/cloudbase
  export TENCENT_SECRET_ID=... TENCENT_SECRET_KEY=... TCB_ENV_ID=...
  export VPS_PG_PASSWORD=...
  uv run --with tencentcloud-sdk-python-tcb --with tencentcloud-sdk-python-tcbr \
     --with "psycopg[binary]" --with requests python api_deploy_verify.py
"""

import io
import json
import os
import secrets
import time
import zipfile
from pathlib import Path

import psycopg
import requests
from tencentcloud.common import credential
from tencentcloud.common.profile.client_profile import ClientProfile
from tencentcloud.common.profile.http_profile import HttpProfile
from tencentcloud.tcb.v20180608 import models as tcb_models
from tencentcloud.tcb.v20180608 import tcb_client
from tencentcloud.tcbr.v20220217 import models as tcbr_models
from tencentcloud.tcbr.v20220217 import tcbr_client

HERE = Path(__file__).resolve().parent
APP_DIR = HERE / "probe-app"

SECRET_ID = os.environ["TENCENT_SECRET_ID"]
SECRET_KEY = os.environ["TENCENT_SECRET_KEY"]
ENV_ID = os.environ["TCB_ENV_ID"]
REGION = os.environ.get("TCB_REGION", "ap-shanghai")
SERVER_NAME = os.environ.get("PROBE_SERVER_NAME", "api-deploy-probe")
KEEP = "--keep" in os.sys.argv

VPS_HOST = os.environ.get("VPS_PG_HOST", "152.32.215.89")
VPS_PORT = int(os.environ.get("VPS_PG_PORT", "10050"))
VPS_ADMIN_USER = os.environ.get("VPS_PG_USER", "root")
VPS_ADMIN_PWD = os.environ["VPS_PG_PASSWORD"]

GAME_ID = "game_apideploy_probe"
ROLE = f"{GAME_ID}_rw"
PWD = secrets.token_urlsafe(16)


def make_clients():
    cred = credential.Credential(SECRET_ID, SECRET_KEY)
    p_tcb = ClientProfile(httpProfile=HttpProfile(endpoint="tcb.tencentcloudapi.com"))
    p_tcbr = ClientProfile(httpProfile=HttpProfile(endpoint="tcbr.tencentcloudapi.com"))
    return (
        tcb_client.TcbClient(cred, REGION, p_tcb),
        tcbr_client.TcbrClient(cred, REGION, p_tcbr),
    )


def req(cls, **kw):
    r = cls()
    for k, v in kw.items():
        setattr(r, k, v)
    return r


def admin(sql, db="postgres"):
    dsn = f"host={VPS_HOST} port={VPS_PORT} dbname={db} user={VPS_ADMIN_USER} password={VPS_ADMIN_PWD} connect_timeout=10"
    with psycopg.connect(dsn, autocommit=True) as c:
        cur = c.execute(sql)
        return cur.fetchall() if cur.description else None


def provision():
    admin(f"select pg_terminate_backend(pid) from pg_stat_activity where datname='{GAME_ID}'")
    admin(f'DROP DATABASE IF EXISTS "{GAME_ID}"')
    admin(f'DROP ROLE IF EXISTS "{ROLE}"')
    admin(f'CREATE DATABASE "{GAME_ID}"')
    admin(f"CREATE ROLE \"{ROLE}\" LOGIN PASSWORD '{PWD}'")
    admin(f'GRANT CONNECT ON DATABASE "{GAME_ID}" TO "{ROLE}"')
    admin('GRANT ALL ON SCHEMA public TO "%s"' % ROLE, db=GAME_ID)
    print(f"[pg] 已开通 db={GAME_ID} role={ROLE}")


def cleanup_db():
    try:
        admin(f"select pg_terminate_backend(pid) from pg_stat_activity where datname='{GAME_ID}'")
        admin(f'DROP DATABASE IF EXISTS "{GAME_ID}"')
        admin(f'DROP ROLE IF EXISTS "{ROLE}"')
        print("[pg] 已清理")
    except Exception as e:
        print("[pg] cleanup error:", repr(e)[:200])


def build_zip() -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for p in sorted(APP_DIR.iterdir()):
            if p.is_file():
                z.write(p, p.name)
    return buf.getvalue()


def deploy(tcb, tcbr_c):
    dsn = f"postgresql://{ROLE}:{PWD}@{VPS_HOST}:{VPS_PORT}/{GAME_ID}"

    zip_bytes = build_zip()
    print(f"[zip] probe-app {len(zip_bytes) / 1024:.1f} KB")

    build = tcb.DescribeCloudBaseBuildService(
        req(tcb_models.DescribeCloudBaseBuildServiceRequest, EnvId=ENV_ID, ServiceName=SERVER_NAME)
    )
    print(f"[build-service] package={build.PackageName} version={build.PackageVersion}")

    headers = {kv.Key: kv.Value for kv in (build.UploadHeaders or [])}
    r = requests.put(build.UploadUrl, data=zip_bytes, headers=headers, timeout=300)
    print(f"[upload] HTTP {r.status_code}")
    r.raise_for_status()

    # 与 manager-node 的 Items 完全一致（见 lib/cloudrun/index.js parseObjectToDiffConfigItem）
    items = [
        req(tcbr_models.DiffConfigItem, Key="AccessTypes", ArrayValue=["PUBLIC"]),
        req(tcbr_models.DiffConfigItem, Key="MinNum", IntValue=0),
        req(tcbr_models.DiffConfigItem, Key="EnvParam", Value=json.dumps({"DATABASE_URL": dsn, "GAME_ID": GAME_ID})),
        req(tcbr_models.DiffConfigItem, Key="InitialDelaySeconds", IntValue=0),
        req(tcbr_models.DiffConfigItem, Key="HasDockerfile", BoolValue=True),
        req(tcbr_models.DiffConfigItem, Key="Port", IntValue=3000),
        req(tcbr_models.DiffConfigItem, Key="Dockerfile", Value="Dockerfile"),
    ]
    deploy_info = req(
        tcbr_models.DeployParam,
        DeployType="package",
        PackageName=build.PackageName,
        PackageVersion=build.PackageVersion,
        ReleaseType="FULL",
    )

    exists = False
    try:
        tcbr_c.DescribeCloudRunServerDetail(
            req(tcbr_models.DescribeCloudRunServerDetailRequest, EnvId=ENV_ID, ServerName=SERVER_NAME)
        )
        exists = True
    except Exception as e:
        print(f"[detail] 服务不存在（{type(e).__name__}），将创建")

    def _do():
        if exists:
            return tcbr_c.UpdateCloudRunServer(
                req(
                    tcbr_models.UpdateCloudRunServerRequest,
                    EnvId=ENV_ID,
                    ServerName=SERVER_NAME,
                    DeployInfo=deploy_info,
                    Items=items,
                )
            )
        return tcbr_c.CreateCloudRunServer(
            req(
                tcbr_models.CreateCloudRunServerRequest,
                EnvId=ENV_ID,
                ServerName=SERVER_NAME,
                DeployInfo=deploy_info,
                Items=items,
            )
        )

    action = "UpdateCloudRunServer" if exists else "CreateCloudRunServer"
    print(f"[deploy] {action} server={SERVER_NAME}", flush=True)
    for attempt in range(12):
        try:
            _do()
            break
        except Exception as e:
            if "ResourceInUse" in str(e) or "运行中" in str(e):
                print(f"[busy] 已有部署任务运行中，30s 后重试（{attempt + 1}/12）", flush=True)
                time.sleep(30)
            else:
                raise
    else:
        raise RuntimeError("部署重试超限")


def wait_ready(tcbr_c, timeout_s=900):
    t0 = time.time()
    last = None
    while time.time() - t0 < timeout_s:
        time.sleep(10)
        try:
            detail = tcbr_c.DescribeCloudRunServerDetail(
                req(tcbr_models.DescribeCloudRunServerDetailRequest, EnvId=ENV_ID, ServerName=SERVER_NAME)
            )
        except Exception as e:
            print(f"[wait] detail error: {repr(e)[:120]}", flush=True)
            continue
        base = getattr(detail, "BaseInfo", None)
        domain = getattr(base, "DefaultDomainName", None) if base else None
        state = getattr(base, "Status", None) if base else None
        if (domain, state) != last:
            print(f"[wait] {int(time.time() - t0)}s status={state} domain={domain}", flush=True)
            last = (domain, state)
        if domain and state in (None, "", "running", "normal", "RUNNING", "NORMAL", "online"):
            return detail
    return None


def probe_http(domain):
    for path in ("/", "/db"):
        for attempt in range(30):
            try:
                r = requests.get(domain.rstrip("/") + path, timeout=20)
                if r.status_code == 200:
                    print(f"[http] GET {path} -> 200 {r.text[:220]}")
                    break
                print(f"[http] GET {path} -> {r.status_code} {r.text[:160]}")
            except Exception as e:
                if attempt == 0 or attempt % 10 == 9:
                    print(f"[http] GET {path} attempt {attempt + 1}: {repr(e)[:120]}")
            time.sleep(6)
        else:
            print(f"[http] GET {path} 未成功")


def main():
    provision()
    tcb, tcbr_c = make_clients()
    try:
        deploy(tcb, tcbr_c)
        detail = wait_ready(tcbr_c)
        if not detail:
            print("[wait] 超时，未拿到默认域名")
            return
        base = getattr(detail, "BaseInfo", None)
        domain = getattr(base, "DefaultDomainName", None) if base else None
        if not domain:
            print("[wait] 未拿到默认域名")
            return
        print(f"[domain] {domain}")
        probe_http(domain)
        try:
            rec = tcbr_c.DescribeCloudRunDeployRecord(
                req(tcbr_models.DescribeCloudRunDeployRecordRequest, EnvId=ENV_ID, ServerName=SERVER_NAME)
            )
            for d in (rec.DeployRecords or [])[:3]:
                print(f"[deploy-record] {d.DeployTime} status={d.Status} flow={getattr(d, 'FlowRatio', '')} buildId={getattr(d, 'BuildId', '')}")
        except Exception as e:
            print("[deploy-record] error:", repr(e)[:150])
        if KEEP:
            print(f"[keep] 保留服务 {SERVER_NAME}（删除：DeleteCloudRunServer）")
    finally:
        if not KEEP:
            try:
                tcbr_c.DeleteCloudRunServer(
                    req(tcbr_models.DeleteCloudRunServerRequest, EnvId=ENV_ID, ServerName=SERVER_NAME)
                )
                print("[cleanup] 云托管服务已删除")
            except Exception as e:
                print("[cleanup] delete error:", repr(e)[:200])
            cleanup_db()


if __name__ == "__main__":
    main()
