"""
SubAgent 并发控制：Semaphore 限流 + 超时保护。
"""

import asyncio
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.core.supervisor.concurrency import SubAgentConcurrencyLimiter

logger = logging.getLogger(__name__)

DEFAULT_MAX_CONCURRENT = 20
DEFAULT_TIMEOUT_SECONDS = 300  # 5 分钟


class _SubAgentPermit:
    """Async context manager returned by SubAgentConcurrencyLimiter.acquire()."""
    __slots__ = ("_limiter", "_name")

    def __init__(self, limiter: "SubAgentConcurrencyLimiter", name: str):
        self._limiter = limiter
        self._name = name

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self._limiter.release(self._name)
        return False


class SubAgentConcurrencyLimiter:
    """
    全局 SubAgent 并发控制（进程级别单例）。

    - Semaphore 控制同时运行的 SubAgent 数量上限（默认 20）
    - 超时保护防止单个 SubAgent 长时间占用资源（默认 5 分钟）
    """

    _instance: "SubAgentConcurrencyLimiter | None" = None

    def __init__(
        self,
        max_concurrent: int = DEFAULT_MAX_CONCURRENT,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
    ):
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._max_concurrent = max_concurrent
        self._timeout_seconds = timeout_seconds
        self._active: int = 0

    @classmethod
    def get_instance(
        cls,
        max_concurrent: int = DEFAULT_MAX_CONCURRENT,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
    ) -> "SubAgentConcurrencyLimiter":
        """获取全局单例。"""
        if cls._instance is None:
            cls._instance = cls(max_concurrent=max_concurrent, timeout_seconds=timeout_seconds)
        return cls._instance

    async def acquire(self, sub_agent_name: str) -> _SubAgentPermit:
        """获取 SubAgent 执行许可，超时则抛出 asyncio.TimeoutError。"""
        logger.info(
            f"[ConcurrencyLimiter] acquiring permit for {sub_agent_name}, "
            f"active={self._active}/{self._max_concurrent}"
        )
        try:
            await asyncio.wait_for(
                self._semaphore.acquire(),
                timeout=self._timeout_seconds,
            )
        except asyncio.TimeoutError:
            logger.error(
                f"[ConcurrencyLimiter] timeout acquiring permit for {sub_agent_name} "
                f"({self._timeout_seconds}s), active={self._active}"
            )
            raise

        self._active += 1
        return _SubAgentPermit(self, sub_agent_name)

    def release(self, sub_agent_name: str) -> None:
        self._semaphore.release()
        self._active -= 1
        logger.info(
            f"[ConcurrencyLimiter] released for {sub_agent_name}, "
            f"active={self._active}/{self._max_concurrent}"
        )

    def active_count(self) -> int:
        return self._active
