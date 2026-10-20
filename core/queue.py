"""排隊：一次只處理一件事，避免同時開很多個 claude -p。"""
from __future__ import annotations

import asyncio
import logging
from collections import Counter
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable

log = logging.getLogger(__name__)

PER_USER_LIMIT = 5


@dataclass
class Job:
    user_id: str
    run: Callable[[], Awaitable[None]]
    payload: Any = None
    on_start: Callable[[], Awaitable[None]] | None = None
    on_error: Callable[[Exception], Awaitable[None]] | None = None
    ahead_note: Any = None  # 「前面還有 N 則」那則訊息，輪到時刪掉
    done: asyncio.Event = field(default_factory=asyncio.Event)


class JobQueue:
    def __init__(self, per_user_limit: int = PER_USER_LIMIT):
        self.q: asyncio.Queue[Job] = asyncio.Queue()
        self.pending: Counter[str] = Counter()  # 每個人排隊中加處理中的數量
        self.running = 0
        self.per_user_limit = per_user_limit

    def ahead(self) -> int:
        """目前在前面的工作數（排隊中加正在處理的）。"""
        return self.q.qsize() + self.running

    def can_accept(self, user_id: str) -> bool:
        return self.pending[user_id] < self.per_user_limit

    def submit(self, job: Job) -> int:
        """加入佇列，回傳加入前在前面的數量。"""
        ahead = self.ahead()
        self.pending[job.user_id] += 1
        self.q.put_nowait(job)
        return ahead

    async def worker(self) -> None:
        while True:
            job = await self.q.get()
            self.running = 1
            try:
                if job.on_start:
                    await job.on_start()
                await job.run()
            except Exception as e:  # 一則壞輸入不能讓整個程式停擺
                log.exception("工作失敗")
                if job.on_error:
                    try:
                        await job.on_error(e)
                    except Exception:
                        log.exception("回報錯誤時又失敗")
            finally:
                self.running = 0
                self.pending[job.user_id] -= 1
                job.done.set()
                self.q.task_done()
