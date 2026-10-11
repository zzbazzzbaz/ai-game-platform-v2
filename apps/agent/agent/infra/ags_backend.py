"""deepagents 沙盒后端适配：AGS（E2B 协议）。

只实现 deepagents `BaseSandbox` 的最小面：execute + 文件上传/下载。
自行适配可绕开 `langchain-e2b` 对 `deepagents<0.7` 的版本约束。
沙盒内访问 COS 挂载点必须 `user="root"`。
"""

from deepagents.backends.protocol import (
    ExecuteResponse,
    FileDownloadResponse,
    FileUploadResponse,
)
from deepagents.backends.sandbox import BaseSandbox
from e2b import Sandbox

from agent.core.constants import SANDBOX_DEFAULT_EXEC_TIMEOUT_SECONDS


class AgsBackend(BaseSandbox):
    enable_capture_offload = True

    def __init__(self, *, sandbox: Sandbox) -> None:
        self._sandbox = sandbox
        self._default_timeout = SANDBOX_DEFAULT_EXEC_TIMEOUT_SECONDS

    @property
    def id(self) -> str:
        return self._sandbox.sandbox_id

    def execute(self, command: str, *, timeout: int | None = None) -> ExecuteResponse:
        effective = timeout if timeout is not None else self._default_timeout
        result = self._sandbox.commands.run(command, timeout=effective, user="root")
        output = result.stdout or ""
        if result.stderr:
            output = f"{output}\n{result.stderr}" if output else result.stderr
        return ExecuteResponse(output=output, exit_code=result.exit_code, truncated=False)

    def download_files(self, paths: list[str]) -> list[FileDownloadResponse]:
        responses: list[FileDownloadResponse] = []
        for path in paths:
            if not path.startswith("/"):
                responses.append(
                    FileDownloadResponse(path=path, content=None, error="invalid_path")
                )
                continue
            try:
                content = self._sandbox.files.read(path, format="bytes")
            except Exception as e:
                message = str(e).lower()
                error = "is_directory" if "directory" in message else "file_not_found"
                responses.append(FileDownloadResponse(path=path, content=None, error=error))
            else:
                responses.append(
                    FileDownloadResponse(path=path, content=bytes(content), error=None)
                )
        return responses

    def upload_files(self, files: list[tuple[str, bytes]]) -> list[FileUploadResponse]:
        responses: list[FileUploadResponse] = []
        for path, content in files:
            if not path.startswith("/"):
                responses.append(FileUploadResponse(path=path, error="invalid_path"))
                continue
            try:
                self._sandbox.files.write(path, bytes(content))
            except Exception:
                responses.append(FileUploadResponse(path=path, error="permission_denied"))
            else:
                responses.append(FileUploadResponse(path=path, error=None))
        return responses
