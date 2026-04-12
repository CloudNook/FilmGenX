import pytest
import asyncio
from app.core.supervisor.concurrency import SubAgentConcurrencyLimiter


def test_semaphore_blocks_when_full():
    """4 个任务使用容量=2 的 Semaphore，全部完成（排队执行）。"""
    limiter = SubAgentConcurrencyLimiter(max_concurrent=2)

    async def fake_subagent(name: str, delay: float = 0.1):
        permit = await limiter.acquire(name)
        async with permit:
            await asyncio.sleep(delay)
            return f"done:{name}"

    async def run():
        results = []
        for i in range(4):
            r = await fake_subagent(f"sub-{i}", delay=0.05)
            results.append(r)
        return results

    results = asyncio.run(run())
    assert len(results) == 4


def test_timeout_raises():
    """容量=1，第一个任务持有 slot，第二个任务 acquire 超时 0.1s。"""
    limiter = SubAgentConcurrencyLimiter(max_concurrent=1, timeout_seconds=0.1)
    timeout_raised = False

    async def hold_slot():
        permit = await limiter.acquire("holder")
        async with permit:
            await asyncio.sleep(2.0)

    async def waiter():
        nonlocal timeout_raised
        try:
            permit = await limiter.acquire("waiter")
            async with permit:
                pass
        except asyncio.TimeoutError:
            timeout_raised = True

    async def run():
        hold = asyncio.create_task(hold_slot())
        await asyncio.sleep(0.05)
        await waiter()
        hold.cancel()

    asyncio.run(run())
    assert timeout_raised, "TimeoutError should have been raised"


def test_active_count():
    """active_count 在任务运行期间 >= 1，结束后归零。"""
    limiter = SubAgentConcurrencyLimiter(max_concurrent=3)

    async def fake(name: str):
        permit = await limiter.acquire(name)
        async with permit:
            assert limiter.active_count() >= 1
            await asyncio.sleep(0.01)

    async def run():
        await asyncio.gather(fake("a"), fake("b"))

    asyncio.run(run())
    assert limiter.active_count() == 0


def test_get_instance_returns_singleton():
    """get_instance 返回同一实例。"""
    limiter1 = SubAgentConcurrencyLimiter.get_instance(max_concurrent=5)
    limiter2 = SubAgentConcurrencyLimiter.get_instance()
    assert limiter1 is limiter2


def test_permit_releases_on_exception():
    """permit 在异常时仍正确 release Semaphore slot。"""
    limiter = SubAgentConcurrencyLimiter(max_concurrent=1)

    async def failing_task():
        permit = await limiter.acquire("fail")
        async with permit:
            raise RuntimeError("boom")

    with pytest.raises(RuntimeError, match="boom"):
        asyncio.run(failing_task())

    # Slot 已释放，新任务可以获取
    async def check():
        permit = await limiter.acquire("after")
        async with permit:
            return "ok"

    result = asyncio.run(check())
    assert result == "ok"
