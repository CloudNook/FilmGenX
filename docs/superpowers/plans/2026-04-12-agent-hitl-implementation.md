# Agent Framework HITL Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add framework-level interrupt/resume HITL capability to the Agent loop, then migrate Supervisor to use it.

**Architecture:** `InterruptConfig` lives on `AgentConfig`. `AgentLoop.stream_run()` checks for interrupts after `ToolEndEvent`. On interrupt, loop yields `InterruptEvent`, saves a checkpoint (messages + loop count) via `PersistStrategy`, and ends the generator. `Agent.resume()` loads the checkpoint, patches messages based on action, and continues the loop from a new `AgentLoop`. Supervisor drops its private `asyncio.Event` HITL code and delegates to the framework.

**Tech Stack:** Python 3.11+, Pydantic, SQLAlchemy (async), Redis, pytest + pytest-asyncio

---

## File Structure

### New Files
| File | Responsibility |
|------|---------------|
| `backend/app/core/agent/checkpoint.py` | `AgentCheckpoint` Pydantic model |
| `backend/app/models/agent_checkpoint.py` | SQLAlchemy ORM model for `agent_checkpoints` table |
| `backend/app/repositories/agent_checkpoint.py` | Async CRUD for checkpoints |
| `backend/app/tests/unit/core/agent/test_interrupt_config.py` | Tests for InterruptConfig, InterruptEvent |
| `backend/app/tests/unit/core/agent/test_agent_resume.py` | Tests for Agent.resume() |
| `backend/app/tests/unit/core/agent/test_checkpoint.py` | Tests for checkpoint save/load |
| `backend/app/tests/unit/core/agent/persist/test_redis_checkpoint.py` | Tests for Redis checkpoint in PersistStrategy |

### Modified Files
| File | Responsibility |
|------|---------------|
| `backend/app/core/agent/base.py` | Add `InterruptConfig`, `InterruptMode`, `InterruptEvent` |
| `backend/app/core/agent/loop.py` | Add interrupt detection in `stream_run()`, checkpoint save |
| `backend/app/core/agent/agent.py` | Add `resume()` method |
| `backend/app/core/agent/factory.py` | Accept `interrupt_config` in `create_agent()` |
| `backend/app/core/agent/persist/base.py` | Add `save_checkpoint`, `load_checkpoint`, `clear_checkpoint` |
| `backend/app/core/agent/persist/redis_strategy.py` | Implement checkpoint methods |
| `backend/app/core/supervisor/supervisor.py` | Remove private HITL, use framework interrupt_config |
| `backend/app/core/supervisor/factory.py` | Accept `interrupt_config`, pass to inner Agent |
| `backend/app/core/supervisor/events.py` | Remove `HumanReviewEvent` |
| `backend/app/core/supervisor/tools.py` | `call_sub_agent` result includes `sub_agent_name` for framework filtering |
| `backend/app/api/v1/endpoints/supervisor.py` | Add `human_review`/`review_nodes` to request, add `GET /state`, `POST /resume` |
| `backend/app/models/supervisor_workflow.py` | Add `hitl_enabled`, `review_nodes` columns |
| `backend/app/services/supervisor_workflow_service.py` | Add `save_interrupt`, `load_interrupt` |

---

## Task 1: Add InterruptConfig and InterruptEvent to base.py

**Files:**
- Modify: `backend/app/core/agent/base.py` (append after existing event classes, ~line 180)
- Test: `backend/app/tests/unit/core/agent/test_interrupt_config.py` (new)

- [ ] **Step 1: Write the failing test**

Create `backend/app/tests/unit/core/agent/test_interrupt_config.py`:

```python
"""Tests for InterruptConfig and InterruptEvent."""
import pytest
from pydantic import ValidationError

from app.core.agent.base import InterruptConfig, InterruptMode, InterruptEvent


class TestInterruptConfig:
    def test_defaults(self):
        cfg = InterruptConfig()
        assert cfg.enabled is False
        assert cfg.mode == InterruptMode.AFTER_TOOL
        assert cfg.tool_names == []
        assert cfg.context == {}

    def test_custom_values(self):
        cfg = InterruptConfig(
            enabled=True,
            mode=InterruptMode.BEFORE_TOOL,
            tool_names=["call_sub_agent"],
            context={"review_sub_agents": ["outline_writer"]},
        )
        assert cfg.enabled is True
        assert cfg.mode == InterruptMode.BEFORE_TOOL
        assert cfg.tool_names == ["call_sub_agent"]

    def test_mode_enum_values(self):
        assert InterruptMode.AFTER_TOOL == "after_tool"
        assert InterruptMode.BEFORE_TOOL == "before_tool"


class TestInterruptEvent:
    def test_basic_construction(self):
        ev = InterruptEvent(
            session_id="sv-123",
            tool_name="call_sub_agent",
            tool_call_id="tc-1",
            tool_result={"output": "hello", "sub_agent_name": "outline_writer"},
        )
        assert ev.type == "interrupt"
        assert ev.session_id == "sv-123"
        assert ev.tool_name == "call_sub_agent"
        assert ev.available_actions == ["approve", "reject", "edit", "skip", "abort"]
        assert ev.context == {}

    def test_with_context(self):
        ev = InterruptEvent(
            session_id="sv-123",
            tool_name="call_sub_agent",
            tool_call_id="tc-1",
            context={"artifacts_snapshot": {"outline_writer": "..."}},
        )
        assert ev.context["artifacts_snapshot"]["outline_writer"] == "..."

    def test_serialization(self):
        ev = InterruptEvent(
            session_id="sv-123",
            tool_name="call_sub_agent",
            tool_call_id="tc-1",
            tool_result={"output": "test"},
        )
        data = ev.model_dump()
        assert data["type"] == "interrupt"
        assert data["session_id"] == "sv-123"
        assert data["tool_result"] == {"output": "test"}

    def test_in_stream_event_union(self):
        from app.core.agent.base import StreamEvent
        ev = InterruptEvent(
            session_id="sv-123",
            tool_name="call_sub_agent",
            tool_call_id="tc-1",
        )
        assert isinstance(ev, StreamEvent)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest app/tests/unit/core/agent/test_interrupt_config.py -v`
Expected: FAIL — `ImportError: cannot import name 'InterruptConfig' from 'app.core.agent.base'`

- [ ] **Step 3: Add InterruptConfig, InterruptMode, InterruptEvent to base.py**

Append to `backend/app/core/agent/base.py`, after the `ErrorEvent` class (around line 177), before the `StreamEvent` union type:

```python
from enum import Enum


class InterruptMode(str, Enum):
    """Interrupt mode for HITL."""
    AFTER_TOOL = "after_tool"
    BEFORE_TOOL = "before_tool"


class InterruptConfig(BaseModel):
    """
    Framework-level HITL interrupt configuration.

    Any Agent created via create_agent() can configure interrupt strategy.
    AgentLoop auto-detects interrupts when conditions match.
    """
    enabled: bool = False
    mode: InterruptMode = InterruptMode.AFTER_TOOL
    tool_names: List[str] = Field(
        default_factory=list,
        description="Tool names that trigger interrupt. Empty = all tools.",
    )
    context: Dict[str, Any] = Field(
        default_factory=dict,
        description="Business-layer context attached to InterruptEvent.",
    )


class InterruptEvent(BaseModel):
    """
    Agent execution interrupted, waiting for external input.

    Framework-level event produced by any Agent with interrupt_config.
    """
    type: Literal["interrupt"] = "interrupt"
    session_id: str
    tool_name: str
    tool_call_id: str
    tool_result: Any = None
    arguments: Dict[str, Any] = Field(default_factory=dict)
    available_actions: List[str] = Field(
        default_factory=lambda: ["approve", "reject", "edit", "skip", "abort"]
    )
    context: Dict[str, Any] = Field(default_factory=dict)
```

Update the `StreamEvent` union type (last line of file, currently ~line 180):

```python
StreamEvent = ThinkingEvent | TextEvent | ToolStartEvent | ToolEndEvent | DoneEvent | ErrorEvent | InterruptEvent
```

Also update `AgentConfig` to include the new field. Add after the `tools` field (around line 61):

```python
    interrupt_config: Optional["InterruptConfig"] = None
```

**Important ordering:** `InterruptMode`, `InterruptConfig`, and `InterruptEvent` must be defined BEFORE `AgentConfig` in `base.py`, because `AgentConfig` references `Optional[InterruptConfig]`. Insert them after the imports and before `AgentConfig` (which is currently around line 50). Use a non-forward `Optional[InterruptConfig]` annotation in `AgentConfig`.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest app/tests/unit/core/agent/test_interrupt_config.py -v`
Expected: All 7 tests PASS

- [ ] **Step 5: Commit**

```bash
cd backend
git add app/core/agent/base.py app/tests/unit/core/agent/test_interrupt_config.py
git commit -m "feat(agent): add InterruptConfig, InterruptMode, InterruptEvent to base"
```

---

## Task 2: Add AgentCheckpoint model

**Files:**
- Create: `backend/app/core/agent/checkpoint.py`
- Test: `backend/app/tests/unit/core/agent/test_checkpoint.py` (new)

- [ ] **Step 1: Write the failing test**

Create `backend/app/tests/unit/core/agent/test_checkpoint.py`:

```python
"""Tests for AgentCheckpoint model."""
import pytest
from datetime import datetime, timezone

from app.core.agent.checkpoint import AgentCheckpoint
from app.core.agent.base import InterruptConfig, InterruptMode


class TestAgentCheckpoint:
    def test_basic_construction(self):
        cp = AgentCheckpoint(
            session_id="sv-123",
            messages=[{"role": "user", "content": "hello"}],
            loop_count=3,
            interrupt_tool_name="call_sub_agent",
            interrupt_config=InterruptConfig(enabled=True, tool_names=["call_sub_agent"]),
        )
        assert cp.session_id == "sv-123"
        assert len(cp.messages) == 1
        assert cp.loop_count == 3
        assert cp.interrupt_tool_name == "call_sub_agent"
        assert cp.created_at is not None

    def test_auto_timestamp(self):
        cp = AgentCheckpoint(
            session_id="sv-123",
            messages=[],
            loop_count=0,
            interrupt_tool_name="call_sub_agent",
            interrupt_config=InterruptConfig(),
        )
        assert isinstance(cp.created_at, datetime)

    def test_serialization_roundtrip(self):
        original = AgentCheckpoint(
            session_id="sv-456",
            messages=[
                {"role": "user", "content": "create a video"},
                {"role": "assistant", "content": "thinking..."},
                {"role": "tool", "tool_call_id": "tc-1", "tool_name": "call_sub_agent", "content": '{"output": "outline text"}'},
            ],
            loop_count=5,
            interrupt_tool_name="call_sub_agent",
            interrupt_config=InterruptConfig(
                enabled=True,
                tool_names=["call_sub_agent"],
                context={"review_sub_agents": ["outline_writer"]},
            ),
        )
        data = original.model_dump()
        restored = AgentCheckpoint(**data)
        assert restored.session_id == original.session_id
        assert restored.messages == original.messages
        assert restored.loop_count == original.loop_count
        assert restored.interrupt_config.context["review_sub_agents"] == ["outline_writer"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest app/tests/unit/core/agent/test_checkpoint.py -v`
Expected: FAIL — `ImportError: cannot import name 'AgentCheckpoint'`

- [ ] **Step 3: Create AgentCheckpoint model**

Create `backend/app/core/agent/checkpoint.py`:

```python
"""
Agent checkpoint model for interrupt/resume HITL.

Serialized snapshot of Agent state at interrupt point,
used to restore execution when human submits review.
"""
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from app.core.agent.base import InterruptConfig


class AgentCheckpoint(BaseModel):
    """
    Snapshot of Agent state at interrupt point.

    Saved by AgentLoop when an interrupt is detected.
    Loaded by Agent.resume() to restore execution.
    """
    session_id: str
    messages: List[Dict[str, Any]]
    loop_count: int
    interrupt_tool_name: str
    interrupt_config: InterruptConfig
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest app/tests/unit/core/agent/test_checkpoint.py -v`
Expected: All 3 tests PASS

- [ ] **Step 5: Commit**

```bash
cd backend
git add app/core/agent/checkpoint.py app/tests/unit/core/agent/test_checkpoint.py
git commit -m "feat(agent): add AgentCheckpoint model for interrupt/resume"
```

---

## Task 3: Extend PersistStrategy with checkpoint methods

**Files:**
- Modify: `backend/app/core/agent/persist/base.py` (add abstract methods)
- Modify: `backend/app/core/agent/persist/redis_strategy.py` (implement)
- Test: `backend/app/tests/unit/core/agent/persist/test_redis_checkpoint.py` (new)

- [ ] **Step 1: Write the failing test**

Create `backend/app/tests/unit/core/agent/persist/test_redis_checkpoint.py`:

```python
"""Tests for Redis checkpoint save/load/clear."""
import pytest
from unittest.mock import AsyncMock, MagicMock

from app.core.agent.checkpoint import AgentCheckpoint
from app.core.agent.base import InterruptConfig
from app.core.agent.persist.redis_strategy import RedisPersistStrategy


@pytest.fixture
def strategy():
    s = RedisPersistStrategy()
    return s


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

            # Verify Redis SET was called
            fake_redis.set.assert_called_once()
            call_args = fake_redis.set.call_args
            assert call_args[0][0] == "agent:checkpoint:sv-test123"

            # Verify load roundtrip
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest app/tests/unit/core/agent/persist/test_redis_checkpoint.py -v`
Expected: FAIL — `AttributeError: 'RedisPersistStrategy' object has no attribute 'save_checkpoint'`

- [ ] **Step 3: Add abstract methods to PersistStrategy base**

Append to `backend/app/core/agent/persist/base.py`, inside the `PersistStrategy` class, after `append_message`:

```python
    @abstractmethod
    async def save_checkpoint(self, checkpoint: "AgentCheckpoint") -> None:
        """
        Save interrupt checkpoint for later resume.

        Called by AgentLoop when an interrupt is detected.
        """
        ...

    @abstractmethod
    async def load_checkpoint(self, session_id: str) -> "Optional[AgentCheckpoint]":
        """
        Load interrupt checkpoint by session_id.

        Returns None if no checkpoint exists for the session.
        Called by Agent.resume() to restore state.
        """
        ...

    @abstractmethod
    async def clear_checkpoint(self, session_id: str) -> None:
        """
        Delete checkpoint after successful resume.

        Called by Agent.resume() after the resumed stream completes.
        """
        ...
```

Add the import at the top of `base.py`:

```python
if TYPE_CHECKING:
    from app.core.agent.checkpoint import AgentCheckpoint
    from app.core.agent.persist.models import AgentMessageRecord, MessageRecord
```

- [ ] **Step 4: Implement checkpoint methods in RedisPersistStrategy**

Append to `backend/app/core/agent/persist/redis_strategy.py`, after `append_message`:

```python
    async def save_checkpoint(self, checkpoint: "AgentCheckpoint") -> None:
        from app.utils import redis_client
        from app.core.agent.checkpoint import AgentCheckpoint

        key = f"agent:checkpoint:{checkpoint.session_id}"
        await redis_client.set(key, checkpoint.model_dump_json().encode())
        await redis_client.expire(key, self.ttl)

    async def load_checkpoint(self, session_id: str) -> "Optional[AgentCheckpoint]":
        from app.utils import redis_client
        from app.core.agent.checkpoint import AgentCheckpoint

        key = f"agent:checkpoint:{session_id}"
        raw = await redis_client.get(key)
        if raw is None:
            return None
        import json
        data = json.loads(raw)
        return AgentCheckpoint(**data)

    async def clear_checkpoint(self, session_id: str) -> None:
        from app.utils import redis_client
        key = f"agent:checkpoint:{session_id}"
        await redis_client.delete(key)
```

Add the missing import at the top:

```python
from typing import Any, Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from app.core.agent.checkpoint import AgentCheckpoint
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd backend && python -m pytest app/tests/unit/core/agent/persist/test_redis_checkpoint.py -v`
Expected: All 3 tests PASS

- [ ] **Step 6: Commit**

```bash
cd backend
git add app/core/agent/persist/base.py app/core/agent/persist/redis_strategy.py app/tests/unit/core/agent/persist/test_redis_checkpoint.py
git commit -m "feat(agent): add checkpoint save/load/clear to PersistStrategy"
```

---

## Task 4: Add interrupt detection to AgentLoop

**Files:**
- Modify: `backend/app/core/agent/loop.py`
- Test: `backend/tests/unit/test_agent_core.py` (add test class)

- [ ] **Step 1: Write the failing test**

Append a new test class to `backend/tests/unit/test_agent_core.py`:

```python
class TestAgentLoopInterrupt:
    """Tests for AgentLoop interrupt detection in stream_run."""

    def _make_interrupt_config(self, tool_names=None):
        from app.core.agent.base import InterruptConfig, InterruptMode
        return InterruptConfig(
            enabled=True,
            mode=InterruptMode.AFTER_TOOL,
            tool_names=tool_names or [],
        )

    def _make_loop_with_interrupt(self, interrupt_config):
        from app.core.agent.loop import AgentLoop
        from app.core.agent.base import AgentConfig
        from unittest.mock import MagicMock

        config = AgentConfig(
            agent_name="test",
            prompt="",
            max_loop=10,
            interrupt_config=interrupt_config,
        )
        return AgentLoop(
            config=config,
            llm=MagicMock(),
            tool_executor=None,
            session_id="test-session",
            request_id="req-1",
            interrupt_config=interrupt_config,
        )

    def test_should_interrupt_disabled(self):
        from app.core.agent.base import InterruptConfig
        loop = self._make_loop_with_interrupt(InterruptConfig(enabled=False))
        assert loop._should_interrupt("any_tool") is False

    def test_should_interrupt_no_config(self):
        from app.core.agent.loop import AgentLoop
        from app.core.agent.base import AgentConfig
        config = AgentConfig(agent_name="test", prompt="")
        loop = AgentLoop(config=config, llm=MagicMock(), session_id="s1")
        assert loop._should_interrupt("any_tool") is False

    def test_should_interrupt_matching_tool(self):
        cfg = self._make_interrupt_config(tool_names=["call_sub_agent"])
        loop = self._make_loop_with_interrupt(cfg)
        assert loop._should_interrupt("call_sub_agent") is True

    def test_should_interrupt_non_matching_tool(self):
        cfg = self._make_interrupt_config(tool_names=["call_sub_agent"])
        loop = self._make_loop_with_interrupt(cfg)
        assert loop._should_interrupt("call_reviewer") is False

    def test_should_interrupt_empty_tool_names_matches_all(self):
        cfg = self._make_interrupt_config(tool_names=[])
        loop = self._make_loop_with_interrupt(cfg)
        assert loop._should_interrupt("any_tool") is True

    def test_should_interrupt_with_context_filter_match(self):
        cfg = self._make_interrupt_config(tool_names=["call_sub_agent"])
        cfg.context["review_sub_agents"] = ["outline_writer"]
        loop = self._make_loop_with_interrupt(cfg)
        result = loop._should_interrupt(
            "call_sub_agent",
            tool_result={"output": "...", "sub_agent_name": "outline_writer"},
        )
        assert result is True

    def test_should_interrupt_with_context_filter_no_match(self):
        cfg = self._make_interrupt_config(tool_names=["call_sub_agent"])
        cfg.context["review_sub_agents"] = ["outline_writer"]
        loop = self._make_loop_with_interrupt(cfg)
        result = loop._should_interrupt(
            "call_sub_agent",
            tool_result={"output": "...", "sub_agent_name": "script_writer"},
        )
        assert result is False

    def test_should_interrupt_before_tool_mode(self):
        from app.core.agent.base import InterruptConfig, InterruptMode
        cfg = InterruptConfig(enabled=True, mode=InterruptMode.BEFORE_TOOL, tool_names=[])
        loop = self._make_loop_with_interrupt(cfg)
        # AFTER_TOOL mode check — should not interrupt when mode is BEFORE_TOOL
        assert loop._should_interrupt("any_tool") is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/unit/test_agent_core.py::TestAgentLoopInterrupt -v`
Expected: FAIL — `TypeError: AgentLoop.__init__() got an unexpected keyword argument 'interrupt_config'`

- [ ] **Step 3: Add interrupt_config to AgentLoop and implement _should_interrupt**

Modify `backend/app/core/agent/loop.py`:

**3a.** Add `interrupt_config` parameter to `AgentLoop.__init__()` (around line 61):

```python
    def __init__(
        self,
        config: AgentConfig,
        llm: LLMAdapter,
        tool_executor: Optional[ToolExecutor] = None,
        persist: Optional[PersistStrategy] = None,
        session_id: str = "",
        request_id: str = "",
        on_loop_start: Optional[Any] = None,
        on_loop_end: Optional[Any] = None,
        interrupt_config: Optional["InterruptConfig"] = None,  # NEW
        initial_messages: Optional[List[Dict[str, Any]]] = None,  # NEW
        initial_loop_count: int = 0,  # NEW
    ):
```

Store them (after existing field assignments):

```python
        self.interrupt_config = interrupt_config
        self.loop_count = initial_loop_count
        if initial_messages is not None:
            self.messages = initial_messages
```

**Important:** The existing `self.loop_count = 0` on line 71 must respect `initial_loop_count`:

```python
        self.loop_count = initial_loop_count
```

**3b.** Add `_should_interrupt` method to `AgentLoop` (after `_check_finished`):

```python
    def _should_interrupt(
        self,
        tool_name: str,
        tool_result: Any = None,
    ) -> bool:
        """Check if this tool execution should trigger an interrupt."""
        if self.interrupt_config is None or not self.interrupt_config.enabled:
            return False
        if self.interrupt_config.mode.value != "after_tool":
            return False
        # Empty tool_names = all tools trigger interrupt
        if not self.interrupt_config.tool_names:
            pass  # match all
        elif tool_name not in self.interrupt_config.tool_names:
            return False
        # Business-layer filter via context
        review_filter = self.interrupt_config.context.get("review_sub_agents")
        if review_filter and tool_result is not None:
            if isinstance(tool_result, dict):
                sub_name = tool_result.get("sub_agent_name", "")
                if sub_name and sub_name not in review_filter:
                    return False
        return True
```

**3c.** Add `_save_checkpoint` method to `AgentLoop` (after `_should_interrupt`):

```python
    async def _save_checkpoint(self, tool_name: str) -> None:
        """Save interrupt checkpoint via persist strategy."""
        if self.persist is None or self.interrupt_config is None:
            return
        from app.core.agent.checkpoint import AgentCheckpoint
        checkpoint = AgentCheckpoint(
            session_id=self.session_id,
            messages=list(self.messages),
            loop_count=self.loop_count,
            interrupt_tool_name=tool_name,
            interrupt_config=self.interrupt_config,
        )
        await self.persist.save_checkpoint(checkpoint)
        logger.info(
            f"[AgentLoop:{self.config.agent_name}] "
            f"Checkpoint saved for session={self.session_id}, tool={tool_name}"
        )
```

**3d.** Add interrupt detection in `stream_run()` — after yielding `ToolEndEvent` (around line 648), before the `on_loop_end` call. Insert between the `yield ToolEndEvent(...)` and the `on_loop_end` / `continue`:

```python
                            yield ToolEndEvent(
                                tool_call_id=tr.tool_call_id,
                                tool_name=tr.tool_name,
                                result=tr.result,
                                is_error=tr.is_error,
                            )

                            # --- Framework-level HITL interrupt check ---
                            if self._should_interrupt(tr.tool_name, tr.result):
                                yield InterruptEvent(
                                    session_id=self.session_id,
                                    tool_name=tr.tool_name,
                                    tool_call_id=tr.tool_call_id,
                                    tool_result=tr.result,
                                    arguments=tc.arguments,
                                    context=self.interrupt_config.context if self.interrupt_config else {},
                                )
                                await self._save_checkpoint(tr.tool_name)
                                # End the generator — SSE stream will close
                                return
```

Add the missing import at the top of `loop.py`:

```python
from app.core.agent.base import (
    # ... existing imports ...
    InterruptEvent,
)
```

Also import `InterruptConfig` in the TYPE_CHECKING block:

```python
from typing import TYPE_CHECKING, Any, Dict, List, Optional

if TYPE_CHECKING:
    from app.core.agent.base import InterruptConfig
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/unit/test_agent_core.py::TestAgentLoopInterrupt -v`
Expected: All 9 tests PASS

- [ ] **Step 5: Run existing tests to verify no regressions**

Run: `cd backend && python -m pytest tests/unit/test_agent_core.py -v`
Expected: All existing tests still PASS (interrupt_config defaults to None, no behavior change)

- [ ] **Step 6: Commit**

```bash
cd backend
git add app/core/agent/loop.py tests/unit/test_agent_core.py
git commit -m "feat(agent): add interrupt detection and checkpoint save to AgentLoop"
```

---

## Task 5: Add Agent.resume() method

**Files:**
- Modify: `backend/app/core/agent/agent.py`
- Test: `backend/app/tests/unit/core/agent/test_agent_resume.py` (new)

- [ ] **Step 1: Write the failing test**

Create `backend/app/tests/unit/core/agent/test_agent_resume.py`:

```python
"""Tests for Agent.resume() method."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from typing import AsyncGenerator

from app.core.agent.agent import Agent
from app.core.agent.base import (
    AgentConfig, AgentResult, DoneEvent, TextEvent,
    InterruptEvent, InterruptConfig,
)
from app.core.agent.checkpoint import AgentCheckpoint


def _make_agent_with_interrupt(interrupt_config=None) -> Agent:
    config = AgentConfig(
        agent_name="test_agent",
        prompt="You are a test agent.",
        max_loop=10,
        interrupt_config=interrupt_config,
    )
    agent = Agent(config=config, session_id="sv-test-resume")
    return agent


class TestAgentResume:
    def test_resume_requires_persist(self):
        """resume() raises ValueError if no persist strategy configured."""
        agent = _make_agent_with_interrupt()
        with pytest.raises(ValueError, match="persist strategy"):
            import asyncio
            asyncio.get_event_loop().run_until_complete(
                agent.resume("approve").__anext__()
            )

    @pytest.mark.asyncio
    async def test_resume_abort_yields_done(self):
        """resume(action='abort') yields DoneEvent immediately."""
        agent = _make_agent_with_interrupt()
        mock_persist = AsyncMock()
        checkpoint = AgentCheckpoint(
            session_id="sv-test-resume",
            messages=[{"role": "user", "content": "test"}],
            loop_count=1,
            interrupt_tool_name="call_sub_agent",
            interrupt_config=InterruptConfig(enabled=True),
        )
        mock_persist.load_checkpoint = AsyncMock(return_value=checkpoint)
        agent.persist = mock_persist

        events = []
        async for ev in agent.resume("abort"):
            events.append(ev)

        assert any(isinstance(e, DoneEvent) for e in events)
        done = [e for e in events if isinstance(e, DoneEvent)][0]
        assert "Aborted" in (done.result.error or "")

    @pytest.mark.asyncio
    async def test_resume_approve_continues_loop(self):
        """resume(action='approve') restores checkpoint and continues stream."""
        agent = _make_agent_with_interrupt(
            InterruptConfig(enabled=True, tool_names=["test_tool"])
        )
        mock_persist = AsyncMock()
        checkpoint = AgentCheckpoint(
            session_id="sv-test-resume",
            messages=[
                {"role": "user", "content": "test"},
                {"role": "assistant", "content": "", "tool_calls": [{"id": "tc-1", "name": "test_tool", "arguments": {}}]},
                {"role": "tool", "tool_call_id": "tc-1", "tool_name": "test_tool", "content": "result"},
            ],
            loop_count=1,
            interrupt_tool_name="test_tool",
            interrupt_config=InterruptConfig(enabled=True, tool_names=["test_tool"]),
        )
        mock_persist.load_checkpoint = AsyncMock(return_value=checkpoint)
        agent.persist = mock_persist

        # Mock LLM to immediately finish
        mock_llm = MagicMock()
        from app.core.agent.base import LLMResponse

        async def fake_stream(*args, **kwargs):
            from app.core.agent.base import LLMResponse
            yield LLMResponse(content="done", finish_reason="stop")

        mock_llm.generate_stream = fake_stream
        agent._llm = mock_llm
        agent._tool_executor = MagicMock()

        events = []
        async for ev in agent.resume("approve"):
            events.append(ev)

        assert any(isinstance(e, DoneEvent) for e in events)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest app/tests/unit/core/agent/test_agent_resume.py -v`
Expected: FAIL — `AttributeError: 'Agent' object has no attribute 'resume'`

- [ ] **Step 3: Implement Agent.resume()**

Add to `backend/app/core/agent/agent.py`, after the `stream()` method (around line 237):

```python
    async def resume(
        self,
        action: str,
        feedback: Optional[str] = None,
        edited_content: Optional[str] = None,
        *,
        request_id: Optional[str] = None,
    ):
        """
        Resume from interrupt checkpoint (streaming).

        Loads checkpoint from persist, patches messages based on action,
        then continues the Agent loop from restored state.

        Args:
            action: "approve" | "reject" | "edit" | "skip" | "abort"
            feedback: Optional feedback text (used with reject)
            edited_content: Replacement content (used with edit)
            request_id: Optional request ID
        """
        if self.persist is None:
            raise ValueError("Cannot resume without a persist strategy")

        await self._inject_skills()
        self._init_llm()
        self._init_tool_executor()

        rid = request_id or str(uuid4())

        # Load checkpoint
        checkpoint = await self.persist.load_checkpoint(self.session_id)
        if checkpoint is None:
            from app.core.agent.base import ErrorEvent
            yield ErrorEvent(error=f"No checkpoint found for session {self.session_id}")
            return

        # Handle abort immediately
        if action == "abort":
            from app.core.agent.base import DoneEvent
            result = AgentResult(
                agent_name=self.config.agent_name,
                error="Aborted by user",
                finished=False,
            )
            yield DoneEvent(result=result)
            await self.persist.clear_checkpoint(self.session_id)
            return

        # Patch messages based on action
        messages = list(checkpoint.messages)

        if action == "approve":
            # No modification needed — tool result stays as-is
            pass
        elif action == "reject":
            messages.append({
                "role": "user",
                "content": f"[Human Review Feedback] {feedback or 'Please revise.'}",
            })
        elif action == "edit":
            if edited_content is not None:
                for msg in reversed(messages):
                    if msg.get("role") == "tool":
                        msg["content"] = edited_content
                        break
        elif action == "skip":
            messages.append({
                "role": "user",
                "content": "[Human Review] Skip this step, proceed to next.",
            })

        # Create new AgentLoop with restored state
        from app.core.agent.loop import AgentLoop
        loop = AgentLoop(
            config=self.config,
            llm=self._llm,
            tool_executor=self._tool_executor,
            persist=self.persist,
            session_id=self.session_id,
            request_id=rid,
            interrupt_config=self.config.interrupt_config,
            initial_messages=messages,
            initial_loop_count=checkpoint.loop_count,
        )

        ctx = self._build_context(rid, "")
        ctx.llm = self._llm
        ctx.loop = loop

        async def _generate():
            async for event in loop.stream_run(""):
                if isinstance(event, DoneEvent):
                    event.result.agent_id = self.agent_id
                    event.result.request_id = rid
                    ctx.result = event.result
                    # Clear checkpoint on successful completion
                    await self.persist.clear_checkpoint(self.session_id)
                yield event

        async for event in self._chain.stream(ctx, _generate()):
            yield event
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest app/tests/unit/core/agent/test_agent_resume.py -v`
Expected: All 3 tests PASS

- [ ] **Step 5: Commit**

```bash
cd backend
git add app/core/agent/agent.py app/tests/unit/core/agent/test_agent_resume.py
git commit -m "feat(agent): add Agent.resume() for interrupt/resume HITL"
```

---

## Task 6: Add interrupt_config to create_agent factory

**Files:**
- Modify: `backend/app/core/agent/factory.py`
- Modify existing test: `backend/app/tests/unit/core/supervisor/test_factory.py` (add a test for interrupt_config passthrough)

- [ ] **Step 1: Add interrupt_config parameter to create_agent**

Modify `backend/app/core/agent/factory.py`:

Add parameter to `create_agent()` signature (after `middlewares`):

```python
    interrupt_config: Optional["InterruptConfig"] = None,
```

Pass it to `AgentConfig`:

```python
    config = AgentConfig(
        agent_name=agent_name,
        prompt=prompt,
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
        tools=tools or [],
        max_loop=max_loop,
        interrupt_config=interrupt_config,
    )
```

Add the import:

```python
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.core.agent.base import InterruptConfig
```

- [ ] **Step 2: Write a test for factory interrupt_config**

Append to `backend/app/tests/unit/core/supervisor/test_factory.py` (or create a quick test inline):

```python
def test_create_agent_with_interrupt_config():
    """create_agent passes interrupt_config to AgentConfig."""
    from app.core.agent.base import InterruptConfig
    from app.core.agent.factory import create_agent

    cfg = InterruptConfig(enabled=True, tool_names=["call_sub_agent"])
    agent = create_agent(
        agent_name="test",
        session_id="s1",
        interrupt_config=cfg,
    )
    assert agent.config.interrupt_config is not None
    assert agent.config.interrupt_config.enabled is True
    assert agent.config.interrupt_config.tool_names == ["call_sub_agent"]
```

- [ ] **Step 3: Run tests**

Run: `cd backend && python -m pytest app/tests/unit/core/supervisor/test_factory.py -v`
Expected: All tests PASS including new one

- [ ] **Step 4: Commit**

```bash
cd backend
git add app/core/agent/factory.py app/tests/unit/core/supervisor/test_factory.py
git commit -m "feat(agent): accept interrupt_config in create_agent factory"
```

---

## Task 7: Migrate Supervisor to use framework HITL

**Files:**
- Modify: `backend/app/core/supervisor/supervisor.py`
- Modify: `backend/app/core/supervisor/events.py`
- Modify: `backend/app/core/supervisor/tools.py`
- Modify: `backend/app/core/supervisor/factory.py`
- Update tests: `backend/app/tests/unit/core/supervisor/test_supervisor.py`, `test_events.py`, `test_factory.py`

- [ ] **Step 1: Remove HumanReviewEvent from events.py**

In `backend/app/core/supervisor/events.py`:

Remove the `HumanReviewEvent` class (lines 56-61).

Remove it from `SupervisorStreamEvent` union:

```python
SupervisorStreamEvent = Union[
    SubAgentStartEvent,
    SubAgentEndEvent,
    ReviewStartEvent,
    ReviewEndEvent,
    SupervisorDoneEvent,
]
```

- [ ] **Step 2: Simplify SupervisorAgent — remove private HITL**

In `backend/app/core/supervisor/supervisor.py`:

**Remove from `__init__`:**
- `self._human_review = human_review`
- `self._review_event = asyncio.Event()`
- `self._review_feedback: Optional[str] = None`
- The `human_review` parameter

**Remove methods:**
- `submit_review()`
- `_inject_feedback_to_prompt()`

**Remove from `stream()`:**
- The entire `if self._human_review and isinstance(event, SubAgentEndEvent):` block (lines 193-217)
- Import of `HumanReviewEvent`

**Add `resume()` method:**

```python
    async def resume(
        self,
        action: str,
        feedback: Optional[str] = None,
        edited_content: Optional[str] = None,
    ) -> AsyncGenerator:
        """Resume Supervisor from interrupt checkpoint."""
        from app.core.agent.base import DoneEvent
        from app.core.supervisor.events import SupervisorDoneEvent

        async for event in self._agent.resume(
            action=action,
            feedback=feedback,
            edited_content=edited_content,
        ):
            # Tag events with supervisor source
            if hasattr(event, "source") and getattr(event, "source", None) is None:
                event.source = "supervisor"

            yield event

            # Wrap DoneEvent with SupervisorDoneEvent
            if isinstance(event, DoneEvent):
                yield SupervisorDoneEvent(
                    supervisor_session_id=self.supervisor_session_id,
                    artifacts=dict(self.context.artifacts),
                    final_result=event.result.raw_output or "Pipeline completed",
                )
```

**Simplified `stream()` — remove all HITL blocking logic:**

```python
    async def stream(self, initial_input: str) -> AsyncGenerator:
        from app.core.supervisor.events import SupervisorDoneEvent

        accumulated_result = ""

        try:
            async for event in self._agent.stream(initial_input):
                if hasattr(event, "source") and getattr(event, "source", None) is None:
                    event.source = "supervisor"
                if hasattr(event, "content") and getattr(event, "type", None) == "text":
                    accumulated_result += event.content
                yield event

            final_artifacts = dict(self.context.artifacts)
            yield SupervisorDoneEvent(
                supervisor_session_id=self.supervisor_session_id,
                artifacts=final_artifacts,
                final_result=accumulated_result or "Pipeline completed",
            )

        except Exception as e:
            logger.exception(f"[SupervisorAgent] stream error: {e}")
            from app.core.agent.base import ErrorEvent
            yield ErrorEvent(error=str(e), source="supervisor")
            yield SupervisorDoneEvent(
                supervisor_session_id=self.supervisor_session_id,
                artifacts=dict(self.context.artifacts),
                final_result=f"Error: {str(e)}",
            )
```

Also remove `asyncio` import (no longer needed for `asyncio.Event`).

- [ ] **Step 3: Update Supervisor factory**

In `backend/app/core/supervisor/factory.py`:

**Remove** `human_review: bool = False` parameter from `create_supervisor()`.

**Add** `interrupt_config: Optional[InterruptConfig] = None` parameter.

Pass `interrupt_config` to the inner Agent via `create_agent()`:

```python
    supervisor._agent = create_agent(
        agent_name="supervisor",
        session_id=supervisor_session_id,
        prompt=supervisor._build_system_prompt(),
        tools=get_supervisor_tool_schemas(),
        max_loop=max_loop,
        persist=persist_strategy,
        middlewares=middlewares,
        interrupt_config=interrupt_config,
    )
```

Wait — `SupervisorAgent.__init__` already creates the inner agent. The interrupt_config needs to flow through there. Modify `SupervisorAgent.__init__` to accept and use it:

```python
    def __init__(
        self,
        supervisor_session_id: str,
        user_request: str,
        sub_agent_configs: Dict[str, Any],
        middlewares: List[AgentMiddleware],
        persist: Optional[PersistStrategy],
        model: str = "gemini-3-flash-preview",
        max_loop: int = 30,
        interrupt_config: Optional[InterruptConfig] = None,  # replaces human_review
    ):
        # ... existing setup ...
        self._agent = create_agent(
            agent_name="supervisor",
            session_id=supervisor_session_id,
            prompt=self._build_system_prompt(),
            tools=tool_schemas,
            max_loop=max_loop,
            persist=persist,
            middlewares=middlewares,
            interrupt_config=interrupt_config,  # NEW
        )
```

**Important:** The inner agent needs a persist strategy for checkpoints. The factory must ensure `persist` is not None when `interrupt_config.enabled` is True.

In `factory.py`, add validation:

```python
    if interrupt_config and interrupt_config.enabled and persist is None:
        persist = "redis"  # default for checkpoint support
```

- [ ] **Step 4: Update call_sub_agent to include sub_agent_name in result**

In `backend/app/core/supervisor/tools.py`, modify the `accumulated_result` dict at line 154 and line 180:

```python
    accumulated_result = {}

    async for event in sub_agent.stream(initial_input=sub_prompt):
        # ... existing event handling ...
        elif isinstance(event, DoneEvent):
            accumulated_result = {
                "output": event.result.raw_output or "",
                "sub_agent_name": sub_agent_name,  # NEW — for framework filtering
            }
```

Also add `sub_agent_name` to the error case (line 167):

```python
        accumulated_result = {"error": str(e), "sub_agent_name": sub_agent_name}
```

- [ ] **Step 5: Update supervisor tests**

Update `backend/app/tests/unit/core/supervisor/test_supervisor.py`:

- Remove any tests referencing `human_review`, `_review_event`, `submit_review`
- Update construction to not pass `human_review`
- Add test for `interrupt_config` passthrough

Update `backend/app/tests/unit/core/supervisor/test_events.py`:

- Remove tests referencing `HumanReviewEvent`
- Remove `HumanReviewEvent` from union test

Update `backend/app/tests/unit/core/supervisor/test_factory.py`:

- Replace `human_review=True` tests with `interrupt_config=InterruptConfig(enabled=True, ...)` tests

- [ ] **Step 6: Run all supervisor tests**

Run: `cd backend && python -m pytest app/tests/unit/core/supervisor/ -v`
Expected: All tests PASS

- [ ] **Step 7: Commit**

```bash
cd backend
git add app/core/supervisor/ app/tests/unit/core/supervisor/
git commit -m "refactor(supervisor): migrate to framework-level HITL, remove private interrupt code"
```

---

## Task 8: Add database migration for HITL fields

**Files:**
- Create: `backend/app/db/migrations/versions/<hash>_add_hitl_fields.py` (alembic revision)
- Create: `backend/app/models/agent_checkpoint.py` (ORM model, optional — can rely on Redis only for MVP)

- [ ] **Step 1: Create migration for supervisor_workflows HITL fields**

Run: `cd backend && alembic revision -m "add_hitl_fields_to_supervisor_workflows"`

Edit the generated migration file:

```python
"""add HITL fields to supervisor_workflows

Revision ID: <auto>
Revises: <auto>
Create Date: 2026-04-12
"""
from alembic import op
import sqlalchemy as sa

revision = "<auto>"
down_revision = "<auto>"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "supervisor_workflows",
        sa.Column("hitl_enabled", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.add_column(
        "supervisor_workflows",
        sa.Column("review_nodes", sa.JSON(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("supervisor_workflows", "review_nodes")
    op.drop_column("supervisor_workflows", "hitl_enabled")
```

- [ ] **Step 2: Update ORM model**

In `backend/app/models/supervisor_workflow.py`, add after the `error_message` field:

```python
    hitl_enabled: Mapped[bool] = mapped_column(
        sa.Boolean,
        nullable=False,
        default=False,
        server_default=sa.text("false"),
        comment="Whether HITL is enabled for this run",
    )
    review_nodes: Mapped[Optional[list]] = mapped_column(
        sa.JSON,
        nullable=True,
        comment="Configured review node names for HITL",
    )
```

Add `import sqlalchemy as sa` at the top.

- [ ] **Step 3: Run migration**

Run: `cd backend && alembic upgrade head`
Expected: Migration applies successfully

- [ ] **Step 4: Commit**

```bash
cd backend
git add app/db/migrations/ app/models/supervisor_workflow.py
git commit -m "feat(db): add hitl_enabled and review_nodes to supervisor_workflows"
```

---

## Task 9: Add API endpoints for resume and state

**Files:**
- Modify: `backend/app/api/v1/endpoints/supervisor.py`
- Modify: `backend/app/services/supervisor_workflow_service.py`
- Test: `backend/app/tests/unit/api/v1/endpoints/test_supervisor_endpoint.py`

- [ ] **Step 1: Add schemas for resume and state**

In `backend/app/api/v1/endpoints/supervisor.py`, add after `SupervisorStartRequest`:

```python
class SupervisorResumeRequest(BaseModel):
    """Resume Supervisor pipeline after human review."""
    action: str = Field(..., description="approve | reject | edit | skip | abort")
    feedback: Optional[str] = Field(None, description="Feedback text (for reject)")
    edited_content: Optional[str] = Field(None, description="Edited content (for edit)")

    @validator("action")
    def validate_action(cls, v):
        if v not in ("approve", "reject", "edit", "skip", "abort"):
            raise ValueError(f"Invalid action: {v}")
        return v


class SupervisorInterruptState(BaseModel):
    """Interrupt state response."""
    status: str
    pending_review_node: Optional[str] = None
    interrupt: Optional[Dict[str, Any]] = None
    artifacts: Optional[Dict[str, Any]] = None
```

Add `from pydantic import BaseModel, Field, validator` to imports.

- [ ] **Step 2: Modify SupervisorStartRequest to include HITL params**

Add to `SupervisorStartRequest`:

```python
    human_review: bool = Field(False, description="Enable human-in-the-loop")
    review_nodes: Optional[List[str]] = Field(None, description="Nodes to review (empty = all)")
```

- [ ] **Step 3: Update _create_supervisor to use interrupt_config**

Modify `_create_supervisor()` in `supervisor.py`:

```python
def _create_supervisor(body: SupervisorStartRequest, user_id: int, workflow_service):
    from app.core.supervisor.factory import create_supervisor
    from app.core.agent.base import InterruptConfig

    persist: Any = None
    if body.persist and body.persist != "none":
        persist = body.persist

    interrupt_config = None
    if body.human_review:
        interrupt_config = InterruptConfig(
            enabled=True,
            tool_names=["call_sub_agent"],
            context={
                "review_sub_agents": body.review_nodes or [],
            },
        )

    return create_supervisor(
        user_request=body.user_request,
        model=body.model,
        max_loop=body.max_loop,
        persist=persist,
        sub_agent_configs=body.sub_agent_configs,
        workflow_service=workflow_service,
        interrupt_config=interrupt_config,
    )
```

- [ ] **Step 4: Add GET /{session_id}/state endpoint**

```python
@router.get(
    "/{session_id}/state",
    summary="Query interrupt state",
)
async def get_interrupt_state(
    session_id: str,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Return current interrupt state for a paused pipeline."""
    from app.services.supervisor_workflow_service import SupervisorWorkflowService
    service = SupervisorWorkflowService(db)
    workflow = await service.get_workflow_by_session(session_id)
    if not workflow:
        from fastapi import HTTPException, status
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    if workflow.status != "waiting_review":
        from fastapi import HTTPException, status
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Session status is '{workflow.status}', not 'waiting_review'",
        )

    # Load checkpoint from persist
    from app.core.agent.persist.redis_strategy import RedisPersistStrategy
    persist = RedisPersistStrategy()
    checkpoint = await persist.load_checkpoint(session_id)

    return SupervisorInterruptState(
        status=workflow.status,
        interrupt={
            "tool_name": checkpoint.interrupt_tool_name if checkpoint else None,
            "context": checkpoint.interrupt_config.context if checkpoint else {},
            "loop_count": checkpoint.loop_count if checkpoint else None,
        },
        artifacts=workflow.artifacts,
    )
```

- [ ] **Step 5: Add POST /{session_id}/resume endpoint**

```python
@router.post(
    "/{session_id}/resume",
    summary="Resume pipeline after human review",
)
async def resume_supervisor_pipeline(
    session_id: str,
    body: SupervisorResumeRequest,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Resume a paused Supervisor pipeline with human review decision."""
    from app.services.supervisor_workflow_service import SupervisorWorkflowService
    service = SupervisorWorkflowService(db)
    workflow = await service.get_workflow_by_session(session_id)
    if not workflow:
        from fastapi import HTTPException, status
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    if workflow.status != "waiting_review":
        from fastapi import HTTPException, status
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Session status is '{workflow.status}', expected 'waiting_review'",
        )

    # Update workflow status back to running
    await service.update_status(session_id, "running")
    await db.commit()

    # Load checkpoint and create SupervisorAgent
    from app.core.agent.persist.redis_strategy import RedisPersistStrategy
    from app.core.agent.base import InterruptConfig
    from app.core.supervisor.factory import create_supervisor

    persist = RedisPersistStrategy()
    checkpoint = await persist.load_checkpoint(session_id)
    if not checkpoint:
        from fastapi import HTTPException, status
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No checkpoint found for session",
        )

    # Rebuild interrupt config from checkpoint
    interrupt_config = checkpoint.interrupt_config

    supervisor = create_supervisor(
        user_request=workflow.user_request,
        model=workflow.model,
        persist="redis",
        interrupt_config=interrupt_config,
    )

    # Restore SupervisorContext artifacts from workflow
    if workflow.artifacts:
        supervisor.context.artifacts.update(workflow.artifacts)

    async def event_stream():
        try:
            async for event in supervisor.resume(
                action=body.action,
                feedback=body.feedback,
                edited_content=body.edited_content,
            ):
                if hasattr(event, "model_dump"):
                    payload = event.model_dump()
                else:
                    payload = {"type": "unknown", "repr": str(event)}
                yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
            yield "data: [DONE]\n\n"
        except Exception as e:
            logger.exception("[supervisor/resume] stream error")
            yield f"data: {json.dumps({'type': 'error', 'error': str(e)}, ensure_ascii=False)}\n\n"
            yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
```

- [ ] **Step 6: Update stream endpoint to save workflow on interrupt**

In `start_supervisor_pipeline()`, after creating the workflow record, also update it when the stream encounters an interrupt. Add to `event_stream()`:

```python
    async def event_stream() -> AsyncGenerator[str, None]:
        try:
            async for event in supervisor.stream(initial_input=body.user_request):
                if hasattr(event, "model_dump"):
                    payload = event.model_dump()
                else:
                    payload = {"type": "unknown", "repr": str(event)}
                yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"

                # Mark workflow as waiting_review on interrupt
                if payload.get("type") == "interrupt":
                    try:
                        await service.update_status(
                            supervisor.supervisor_session_id, "waiting_review"
                        )
                        await db.commit()
                    except Exception as e:
                        logger.warning(f"[supervisor/stream] failed to update status: {e}")

            yield "data: [DONE]\n\n"
        except Exception as e:
            # ... existing error handling ...
```

- [ ] **Step 7: Add SupervisorWorkflowService.update_status**

In `backend/app/services/supervisor_workflow_service.py`, add:

```python
    async def update_status(
        self,
        supervisor_session_id: str,
        status: str,
    ) -> Optional[SupervisorWorkflow]:
        """Update workflow status."""
        workflow = await self.repo.get_by_session_id(supervisor_session_id)
        if not workflow:
            return None
        workflow.status = status
        if status == "completed":
            from datetime import datetime, timezone
            workflow.completed_at = datetime.now(timezone.utc)
        await self.db.commit()
        await self.db.refresh(workflow)
        return workflow
```

- [ ] **Step 8: Run tests**

Run: `cd backend && python -m pytest app/tests/unit/api/v1/endpoints/test_supervisor_endpoint.py -v`
Expected: All tests PASS

- [ ] **Step 9: Commit**

```bash
cd backend
git add app/api/v1/endpoints/supervisor.py app/services/supervisor_workflow_service.py app/tests/unit/api/v1/endpoints/test_supervisor_endpoint.py
git commit -m "feat(api): add HITL resume/state endpoints and interrupt config to start"
```

---

## Task 10: Update E2E supervisor test for framework HITL

**Files:**
- Modify: `backend/app/tests/e2e/supervisor/test_e2e_supervisor.py`
- Modify: `backend/tests/e2e/test_supervisor_real.py`

- [ ] **Step 1: Update mock E2E test**

Update `backend/app/tests/e2e/supervisor/test_e2e_supervisor.py`:

- Replace `human_review=True` with `interrupt_config=InterruptConfig(enabled=True, tool_names=["call_sub_agent"])`
- Replace `supervisor.submit_review(feedback=None)` with verifying that `InterruptEvent` is yielded
- Add test for `supervisor.resume("approve")` producing continuation events

- [ ] **Step 2: Update real E2E test**

Update `backend/tests/e2e/test_supervisor_real.py`:

- Replace `create_supervisor(..., human_review=True)` with `interrupt_config=InterruptConfig(enabled=True, tool_names=["call_sub_agent"])`
- Replace `supervisor.submit_review()` with collecting `InterruptEvent` then calling `supervisor.resume("approve")`

- [ ] **Step 3: Run E2E mock test**

Run: `cd backend && python -m pytest app/tests/e2e/supervisor/test_e2e_supervisor.py -v`
Expected: All tests PASS

- [ ] **Step 4: Commit**

```bash
cd backend
git add app/tests/e2e/supervisor/ tests/e2e/
git commit -m "test(supervisor): update E2E tests for framework-level HITL"
```

---

## Task 11: Final validation and cleanup

**Files:**
- All changed files

- [ ] **Step 1: Run full test suite**

Run: `cd backend && python -m pytest app/tests/ tests/unit/ -v --tb=short`
Expected: All tests PASS, no regressions

- [ ] **Step 2: Verify import consistency**

Run: `cd backend && python -c "from app.core.agent.base import InterruptConfig, InterruptEvent, InterruptMode, AgentCheckpoint; print('OK')"`
Expected: `OK`

- [ ] **Step 3: Verify supervisor creates with interrupt_config**

Run: `cd backend && python -c "
from app.core.supervisor.factory import create_supervisor
from app.core.agent.base import InterruptConfig
s = create_supervisor(user_request='test', interrupt_config=InterruptConfig(enabled=True, tool_names=['call_sub_agent']))
print(f'agent interrupt_config: {s._agent.config.interrupt_config}')
print('OK')
"`
Expected: Prints interrupt config and `OK`

- [ ] **Step 4: Run existing validation script**

Run: `cd backend && python validate_supervisor.py`
Expected: All validation sections PASS

- [ ] **Step 5: Final commit**

```bash
cd backend
git add -A
git commit -m "chore: final validation for agent framework HITL implementation"
```
