"""AGS 沙盒网关（E2B 兼容协议；每游戏一个；COS 存储挂载）。

- 数据面 = E2B 官方 SDK；`metadata["x-mounts"]` 为 AGS 私有扩展（细节见 `docs/chat/10.8/03-验证结论与坑.md`）。
- 沙盒内访问挂载点必须以 `user="root"` 执行；挂载路径 `/workspace/{work,input}`。
- 实例 ID 落 `games.sandbox_id`，创建 / 复用；沙盒有生命周期（timeout）。
"""

import json

from e2b import Sandbox
from e2b.sandbox.commands.command_handle import CommandExitException

from app.core.constants import (
    SANDBOX_CDP_PORT,
    SANDBOX_INPUT_ROOT,
    SANDBOX_NOVNC_PORT,
    SANDBOX_WORK_ROOT,
)
from app.core.exceptions import UpstreamError


class AgsGateway:
    def __init__(
        self, *, domain: str, api_key: str, template: str, timeout_seconds: int
    ) -> None:
        self._domain = domain
        self._api_key = api_key
        self._template = template
        self._timeout_seconds = timeout_seconds

    def _kwargs(self) -> dict:
        return {"api_key": self._api_key, "domain": self._domain}

    def connect(self, sandbox_id: str) -> Sandbox | None:
        try:
            return Sandbox.connect(sandbox_id, **self._kwargs())
        except Exception:
            return None

    def _require(self, sandbox_id: str) -> Sandbox:
        sandbox = self.connect(sandbox_id)
        if sandbox is None:
            raise UpstreamError("沙盒不存在或已过期，请重新进入游戏会话")
        return sandbox

    def ensure(self, *, game_id: str, sandbox_id: str | None, envs: dict | None) -> tuple[str, bool]:
        """创建 / 复用沙盒。返回 (sandbox_id, created)。"""
        if sandbox_id:
            existing = self.connect(sandbox_id)
            if existing is not None:
                return sandbox_id, False
        mounts = [
            {"name": "work", "subPath": str(game_id), "mountPath": SANDBOX_WORK_ROOT},
            {
                "name": "work",
                "subPath": f"{game_id}/input",
                "mountPath": SANDBOX_INPUT_ROOT,
                "readOnly": True,
            },
        ]
        kwargs: dict = {
            "template": self._template,
            "timeout": self._timeout_seconds,
            "metadata": {"game_id": str(game_id), "x-mounts": json.dumps(mounts)},
            **self._kwargs(),
        }
        if envs:
            kwargs["envs"] = envs
        try:
            sandbox = Sandbox.create(**kwargs)
        except Exception as e:
            raise UpstreamError(f"沙盒创建失败：{e}") from e
        return sandbox.sandbox_id, True

    def run(
        self, sandbox_id: str, command: str, *, user: str = "root", timeout: int = 60
    ) -> tuple[int, str, str]:
        sandbox = self._require(sandbox_id)
        try:
            result = sandbox.commands.run(command, timeout=timeout, user=user)
        except CommandExitException as e:
            # e2b 对非 0 退出码抛异常；统一转成 (code, stdout, stderr) 返回
            return e.exit_code, e.stdout or "", e.stderr or ""
        except Exception as e:
            raise UpstreamError(f"沙盒命令执行失败：{e}") from e
        return result.exit_code, result.stdout or "", result.stderr or ""

    def write_file(self, sandbox_id: str, path: str, data: bytes) -> None:
        sandbox = self._require(sandbox_id)
        try:
            sandbox.files.write(path, data)
        except Exception as e:
            raise UpstreamError(f"沙盒文件写入失败：{path}") from e

    def read_file(self, sandbox_id: str, path: str) -> bytes | None:
        sandbox = self._require(sandbox_id)
        try:
            return bytes(sandbox.files.read(path, format="bytes"))
        except Exception:
            return None

    def preview_url(self, sandbox_id: str) -> str:
        """开发期预览：直连 NoVNC（含令牌；上线前改同源反代，R-PRE-1/2/4）。"""
        sandbox = self._require(sandbox_id)
        host = sandbox.get_host(SANDBOX_NOVNC_PORT)
        token = sandbox._envd_access_token
        return (
            f"https://{host}/novnc/vnc.html"
            f"?access_token={token}&path=websockify%3Faccess_token%3D{token}"
            f"&autoconnect=1&resize=scale"
        )

    def cdp_url(self, sandbox_id: str) -> str:
        sandbox = self._require(sandbox_id)
        host = sandbox.get_host(SANDBOX_CDP_PORT)
        token = sandbox._envd_access_token
        return f"https://{host}/cdp?access_token={token}"

    def kill(self, sandbox_id: str) -> None:
        sandbox = self.connect(sandbox_id)
        if sandbox is not None:
            try:
                sandbox.kill()
            except Exception:
                pass
