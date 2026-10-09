import modal
from deepagents.backends.protocol import (
    ExecuteResponse,
    FileDownloadResponse,
    FileUploadResponse,
)
from deepagents.backends.sandbox import BaseSandbox
from modal.exception import (
    SandboxFilesystemError,
    SandboxFilesystemIsADirectoryError,
    SandboxFilesystemPermissionError,
)

from agent.core.constants import SANDBOX_DEFAULT_EXEC_TIMEOUT_SECONDS

_MISSING = (FileNotFoundError, SandboxFilesystemError)


class ModalBackend(BaseSandbox):
    def __init__(self, *, sandbox: modal.Sandbox) -> None:
        self._sandbox = sandbox
        self._default_timeout = SANDBOX_DEFAULT_EXEC_TIMEOUT_SECONDS

    @property
    def id(self) -> str:
        return self._sandbox.object_id

    def execute(self, command: str, *, timeout: int | None = None) -> ExecuteResponse:
        effective = timeout if timeout is not None else self._default_timeout
        process = self._sandbox.exec("bash", "-c", command, timeout=effective)
        process.wait()
        stdout = process.stdout.read()
        stderr = process.stderr.read()
        output = stdout or ""
        if stderr:
            output += "\n" + stderr if output else stderr
        return ExecuteResponse(output=output, exit_code=process.returncode, truncated=False)

    def download_files(self, paths: list[str]) -> list[FileDownloadResponse]:
        responses = []
        for path in paths:
            if not path.startswith("/"):
                responses.append(
                    FileDownloadResponse(path=path, content=None, error="invalid_path")
                )
                continue
            try:
                content = self._sandbox.filesystem.read_bytes(path)
            except SandboxFilesystemIsADirectoryError:
                responses.append(
                    FileDownloadResponse(path=path, content=None, error="is_directory")
                )
            except _MISSING:
                responses.append(
                    FileDownloadResponse(path=path, content=None, error="file_not_found")
                )
            else:
                responses.append(
                    FileDownloadResponse(path=path, content=bytes(content), error=None)
                )
        return responses

    def upload_files(self, files: list[tuple[str, bytes]]) -> list[FileUploadResponse]:
        responses = []
        for path, content in files:
            if not path.startswith("/"):
                responses.append(FileUploadResponse(path=path, error="invalid_path"))
                continue
            try:
                self._sandbox.filesystem.write_bytes(bytes(content), path)
            except SandboxFilesystemPermissionError:
                responses.append(FileUploadResponse(path=path, error="permission_denied"))
            except _MISSING:
                responses.append(FileUploadResponse(path=path, error="file_not_found"))
            else:
                responses.append(FileUploadResponse(path=path, error=None))
        return responses
