"""极简后台执行器：守护线程 + FIFO 队列。

用途：API 进程内的异步发布。不用 `ThreadPoolExecutor` 的原因是其工作线程非守护，
进程退出时会 join 未完成任务（一次部署可能几分钟）；这里用守护线程，进程退出即放弃，
由启动对账把残留的 deploying 版本标记为失败。
"""

import logging
from collections.abc import Callable
from queue import Queue
from threading import Thread

logger = logging.getLogger(__name__)


class DaemonExecutor:
    def __init__(self, *, max_workers: int, thread_name_prefix: str) -> None:
        self._queue: Queue[Callable[[], None] | None] = Queue()
        self._closed = False
        self._threads = [
            Thread(
                target=self._work,
                name=f"{thread_name_prefix}-{index}",
                daemon=True,
            )
            for index in range(max_workers)
        ]
        for thread in self._threads:
            thread.start()

    def _work(self) -> None:
        while True:
            job = self._queue.get()
            if job is None:
                return
            try:
                job()
            except Exception:
                logger.exception("后台任务异常")

    def submit(self, job: Callable[[], None], /) -> None:
        if self._closed:
            raise RuntimeError("后台执行器已关闭")
        self._queue.put(job)

    def shutdown(self) -> None:
        self._closed = True
        for _ in self._threads:
            self._queue.put(None)
