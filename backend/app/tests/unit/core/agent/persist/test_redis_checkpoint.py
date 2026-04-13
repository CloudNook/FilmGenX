"""Tests for Redis checkpoint save/load/clear."""
import pytest
from unittest.mock import AsyncMock

from app.core.agent.checkpoint import AgentCheckpoint
from app.core.agent.base import InterruptConfig
from app.core.agent.persist.redis_strategy import RedisPersistStrategy


@pytest.fixture
def strategy():
    return RedisPersistStrategy()


@pytest.fixture
def sample_checkpoint():
    return AgentCheckpoint(
        session_id="sv-test123",
        messages=[
            {"role": "user", "content": "create a video"},
            {"role": "assistant", "content": "ok"},
        ],
        loop_count=3,
        interrupt_tool_name="call_sub_agent",
        interrupt_config=InterruptConfig(enabled=True, tool_names=["call_sub_agent"]),
    )


class TestRedisCheckpoint:
    @pytest.mark.asyncio
    async def test_save_and_load(self, strategy, sample_checkpoint):
        """save_checkpoint stores to Redis, load_checkpoint retrieves it."""
        fake_redis = AsyncMock()
        fake_redis.set = AsyncMock()
        fake_redis.get = AsyncMock(return_value=sample_checkpoint.model_dump_json().encode())
        fake_redis.expire = AsyncMock()
        fake_redis.delete = AsyncMock()

        import app.utils
        with pytest.MonkeyPatch.context() as m:
            m.setattr(app.utils, "redis_client", fake_redis)

            await strategy.save_checkpoint(sample_checkpoint)

            fake_redis.set.assert_called_once()
            call_args = fake_redis.set.call_args
            assert call_args[0][0] == "agent:checkpoint:sv-test123"

            loaded = await strategy.load_checkpoint("sv-test123")
            assert loaded is not None
            assert loaded.session_id == "sv-test123"
            assert loaded.loop_count == 3
            assert len(loaded.messages) == 2

    @pytest.mark.asyncio
    async def test_load_nonexistent(self, strategy):
        """load_checkpoint returns None for missing session."""
        fake_redis = AsyncMock()
        fake_redis.get = AsyncMock(return_value=None)

        import app.utils
        with pytest.MonkeyPatch.context() as m:
            m.setattr(app.utils, "redis_client", fake_redis)
            result = await strategy.load_checkpoint("sv-nonexistent")
            assert result is None

    @pytest.mark.asyncio
    async def test_clear_checkpoint(self, strategy):
        """clear_checkpoint deletes the Redis key."""
        fake_redis = AsyncMock()
        fake_redis.delete = AsyncMock()

        import app.utils
        with pytest.MonkeyPatch.context() as m:
            m.setattr(app.utils, "redis_client", fake_redis)
            await strategy.clear_checkpoint("sv-test123")
            fake_redis.delete.assert_called_once_with("agent:checkpoint:sv-test123")
