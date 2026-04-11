# Supervisor Agent 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现 Supervisor Agent 框架，支持动态调用 SubAgent（大纲/剧本/分镜），SubAgent 结果通过独立 Reviewer 评估，流式 SSE 实时透传到前端。

**Architecture:** Supervisor 是一个标准的 Meta-Agent，拥有独立 session 和 LLM。它通过 `call_sub_agent` 工具动态创建并执行 SubAgent，通过 `call_reviewer` 调用 Reviewer Agent 评估质量，通过 `get_workflow_state` 查询流水线状态。SubAgent 的流式事件实时透传到 SSE。

**Tech Stack:** Python 3.11+, FastAPI, Pydantic, Redis, asyncio

---

## 文件结构

```
backend/app/core/supervisor/
├── context.py          # SupervisorContext（Pydantic，流水线工作内存）
├── session.py          # SupervisorSession（SubAgent session 关联管理）
├── events.py           # SupervisorStreamEvent 扩展 + source 标记
├── tools.py            # call_sub_agent / call_reviewer / get_workflow_state 工具
├── reviewer.py         # Reviewer Agent 配置和 prompt
├── supervisor.py       # SupervisorAgent 核心类
├── factory.py          # create_supervisor() 工厂
├── workflow.py         # SupervisorWorkflow ORM 模型（DB）
└── workflow_service.py # 流水线元信息读写服务

backend/app/core/
├── agent/tool.py       # MODIFY: ToolExecutor 新增 execute_streaming_tool() 方法
└── agent/persist/
    └── models.py       # MODIFY: agent_messages 表新增 supervisor_session_id 字段

backend/app/core/tools/
└── supervisor_tools.py  # 导入 supervisor.tools 以触发 @register_tool 装饰器
```

---

## 任务概览

| # | 任务 | 文件 |
|---|------|------|
| 1 | SupervisorContext 模型 | `context.py` |
| 2 | SupervisorSession 管理类 | `session.py` |
| 3 | SupervisorStreamEvent 扩展 | `events.py` |
| 4 | ToolExecutor 流式工具支持 | `agent/tool.py` |
| 5 | call_sub_agent 工具 | `tools.py` |
| 6 | call_reviewer + get_workflow_state 工具 | `tools.py` |
| 7 | Reviewer Agent 配置 | `reviewer.py` |
| 8 | SupervisorAgent 核心类 | `supervisor.py` |
| 9 | create_supervisor() 工厂 | `factory.py` |
| 10 | 工具注册入口 | `tools/supervisor_tools.py` |
| 11 | API 路由集成 | `api/supervisor.py` |
| 12 | `supervisor_workflows` 表 | `agent/persist/models.py` |
| 13 | `agent_messages` 表加字段 | `agent/persist/models.py` |
| 14 | SupervisorWorkflow Service | `supervisor/workflow_service.py` |
| 15 | DB 持久化改造 `call_sub_agent` | `supervisor/tools.py` |

---

## Task 1: SupervisorContext

**Files:**
- Create: `backend/app/core/supervisor/context.py`
- Tests: `backend/app/tests/unit/core/supervisor/test_context.py`

- [ ] **Step 1: 创建目录和测试文件**

```bash
mkdir -p backend/app/core/supervisor
mkdir -p backend/app/tests/unit/core/supervisor
```

```python
# backend/app/tests/unit/core/supervisor/test_context.py
import pytest
from app.core.supervisor.context import SupervisorContext


def test_supervisor_context_defaults():
    ctx = SupervisorContext(
        supervisor_session_id="sv-abc123",
        user_request="生成一个科幻短片剧本",
    )
    assert ctx.supervisor_session_id == "sv-abc123"
    assert ctx.user_request == "生成一个科幻短片剧本"
    assert ctx.current_phase == "init"
    assert ctx.artifacts == {}
    assert ctx.sub_agent_sessions == {}
    assert ctx.review_history == []


def test_supervisor_context_update_artifacts():
    ctx = SupervisorContext(
        supervisor_session_id="sv-abc123",
        user_request="生成一个科幻短片剧本",
    )
    ctx.artifacts["outline"] = {"title": "星际穿越", "scenes": 5}
    assert ctx.artifacts["outline"]["title"] == "星际穿越"


def test_supervisor_context_register_sub_session():
    ctx = SupervisorContext(
        supervisor_session_id="sv-abc123",
        user_request="生成一个科幻短片剧本",
    )
    ctx.sub_agent_sessions["outline_writer"] = "sub-outline-001"
    assert ctx.sub_agent_sessions["outline_writer"] == "sub-outline-001"
```

- [ ] **Step 2: 运行测试，确认失败**

```bash
cd backend && python -m pytest app/tests/unit/core/supervisor/test_context.py -v
```
Expected: FAIL — module not found

- [ ] **Step 3: 编写实现**

```python
# backend/app/core/supervisor/context.py
"""
Supervisor 流水线工作内存。
"""

from typing import Any, Dict, List, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


class SupervisorContext(BaseModel):
    """
    Supervisor 的工作内存，所有 SubAgent 可访问。

    注意：SubAgent 不直接访问此对象。
    Supervisor 通过 call_sub_agent 的 context_snapshot 参数选择性注入必要数据。
    """

    supervisor_session_id: str = Field(..., description="Supervisor session ID")
    user_request: str = Field(..., description="用户原始需求")
    current_phase: str = Field(
        default="init",
        description="当前流水线阶段：init | outline | script | storyboard | review | done",
    )
    artifacts: Dict[str, Any] = Field(
        default_factory=dict,
        description="各阶段产物：{outline: {...}, script: {...}, storyboard: {...}}",
    )
    sub_agent_sessions: Dict[str, str] = Field(
        default_factory=dict,
        description="sub_agent_name → session_id 的映射",
    )
    review_history: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="评估历史：[{agent, score, passed, feedback}, ...]",
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="附加元数据",
    )
```

- [ ] **Step 4: 运行测试，确认通过**

```bash
cd backend && python -m pytest app/tests/unit/core/supervisor/test_context.py -v
```
Expected: PASS

- [ ] **Step 5: 提交**

```bash
cd backend && git add app/core/supervisor/context.py app/tests/unit/core/supervisor/test_context.py && git commit -m "feat(supervisor): add SupervisorContext model"
```
---

## Task 2: SupervisorSession

**Files:**
- Create: `backend/app/core/supervisor/session.py`
- Tests: `backend/app/tests/unit/core/supervisor/test_session.py`

- [ ] **Step 1: 编写测试**

```python
# backend/app/tests/unit/core/supervisor/test_session.py
import pytest
from app.core.supervisor.session import SupervisorSession


def test_register_and_get_sub_session():
    session = SupervisorSession("sv-abc123")
    session.register_sub_session("outline_writer", "sub-outline-001")
    assert session.get_sub_session("outline_writer") == "sub-outline-001"


def test_get_all_sessions():
    session = SupervisorSession("sv-abc123")
    session.register_sub_session("outline_writer", "sub-outline-001")
    session.register_sub_session("script_writer", "sub-script-002")
    all_sessions = session.get_all_sessions()
    assert len(all_sessions) == 2
    assert all_sessions["outline_writer"] == "sub-outline-001"


def test_get_nonexistent_session():
    session = SupervisorSession("sv-abc123")
    assert session.get_sub_session("nonexistent") is None


def test_session_id_format():
    session = SupervisorSession("sv-abc123")
    assert session.supervisor_session_id == "sv-abc123"
```

- [ ] **Step 2: 运行测试，确认失败**

```bash
cd backend && python -m pytest app/tests/unit/core/supervisor/test_session.py -v
```
Expected: FAIL — module not found

- [ ] **Step 3: 编写实现**

```python
# backend/app/core/supervisor/session.py
"""
Supervisor 与 SubAgent 的 session 关联管理。
"""

from typing import Dict, Optional


class SupervisorSession:
    """
    管理 Supervisor 与 SubAgent 的 session 关联。

    Supervisor 拥有独立的 supervisor_session_id。
    每个 SubAgent 也有自己的 sub_session_id，通过此对象记录关联关系。
    """

    def __init__(self, supervisor_session_id: str):
        self.supervisor_session_id = supervisor_session_id
        self._sub_sessions: Dict[str, str] = {}

    def register_sub_session(self, sub_agent_name: str, sub_session_id: str) -> None:
        """记录一个 SubAgent 的 session_id。"""
        self._sub_sessions[sub_agent_name] = sub_session_id

    def get_sub_session(self, sub_agent_name: str) -> Optional[str]:
        """获取指定 SubAgent 的 session_id，不存在返回 None。"""
        return self._sub_sessions.get(sub_agent_name)

    def get_all_sessions(self) -> Dict[str, str]:
        """返回所有 SubAgent session_id 的副本。"""
        return dict(self._sub_sessions)
```

- [ ] **Step 4: 运行测试，确认通过**

```bash
cd backend && python -m pytest app/tests/unit/core/supervisor/test_session.py -v
```
Expected: PASS

- [ ] **Step 5: 提交**

```bash
cd backend && git add app/core/supervisor/session.py app/tests/unit/core/supervisor/test_session.py && git commit -m "feat(supervisor): add SupervisorSession for session management"
```
---

## Task 3: SupervisorStreamEvent 扩展

**Files:**
- Create: `backend/app/core/supervisor/events.py`
- Tests: `backend/app/tests/unit/core/supervisor/test_events.py`

- [ ] **Step 1: 编写测试**

```python
# backend/app/tests/unit/core/supervisor/test_events.py
import pytest
from app.core.supervisor.events import (
    SubAgentStartEvent,
    SubAgentEndEvent,
    ReviewStartEvent,
    ReviewEndEvent,
    SupervisorDoneEvent,
    SupervisorStreamEvent,
)


def test_sub_agent_start_event():
    event = SubAgentStartEvent(
        sub_agent_name="outline_writer",
        session_id="sub-outline-001",
        task_description="生成视频大纲",
    )
    assert event.type == "sub_agent_start"
    assert event.sub_agent_name == "outline_writer"
    assert event.source == "supervisor"


def test_sub_agent_end_event():
    event = SubAgentEndEvent(
        sub_agent_name="outline_writer",
        session_id="sub-outline-001",
        result={},  # AgentResult-like dict
    )
    assert event.type == "sub_agent_end"
    assert event.review_result is None


def test_review_end_event():
    event = ReviewEndEvent(
        sub_agent_name="outline_writer",
        score=8.5,
        passed=True,
        feedback="结构完整，逻辑清晰",
    )
    assert event.passed is True
    assert event.score == 8.5


def test_supervisor_done_event():
    event = SupervisorDoneEvent(
        supervisor_session_id="sv-abc123",
        artifacts={"outline": {"title": "星际穿越"}},
        final_result="流水线执行完毕",
    )
    assert event.supervisor_session_id == "sv-abc123"
    assert event.artifacts["outline"]["title"] == "星际穿越"


def test_stream_event_union_type():
    """验证 SupervisorStreamEvent 联合类型包含所有预期事件类型。"""
    from typing import get_args
    event_types = get_args(SupervisorStreamEvent)
    type_names = [t.__name__ for t in event_types]
    assert "SubAgentStartEvent" in type_names
    assert "SubAgentEndEvent" in type_names
    assert "ReviewStartEvent" in type_names
    assert "ReviewEndEvent" in type_names
    assert "SupervisorDoneEvent" in type_names
```

- [ ] **Step 2: 运行测试，确认失败**

```bash
cd backend && python -m pytest app/tests/unit/core/supervisor/test_events.py -v
```
Expected: FAIL — module not found

- [ ] **Step 3: 编写实现**

```python
# backend/app/core/supervisor/events.py
"""
Supervisor 流水线流式事件扩展。

在 app.core.agent.base.StreamEvent 基础上新增：
- SubAgentStartEvent / SubAgentEndEvent
- ReviewStartEvent / ReviewEndEvent
- SupervisorDoneEvent

每个事件携带 source 字段，用于前端渲染区分来源。
"""

from typing import Any, Dict, List, Literal, Optional, Union

from app.core.agent.base import StreamEvent


class SubAgentStartEvent(StreamEvent):
    """SubAgent 开始执行。"""
    type: Literal["sub_agent_start"] = "sub_agent_start"
    sub_agent_name: str
    session_id: str
    task_description: str
    source: str = "supervisor"  # 前端渲染标识：当前活跃的 SubAgent


class SubAgentEndEvent(StreamEvent):
    """SubAgent 执行完毕。"""
    type: Literal["sub_agent_end"] = "sub_agent_end"
    sub_agent_name: str
    session_id: str
    result: Dict[str, Any]  # AgentResult.schema_data
    review_result: Optional[Dict[str, Any]] = None  # 可选，Reviewer 评估结果


class ReviewStartEvent(StreamEvent):
    """Reviewer Agent 开始评估。"""
    type: Literal["review_start"] = "review_start"
    sub_agent_name: str
    criteria: List[str]
    source: str = "supervisor"


class ReviewEndEvent(StreamEvent):
    """Reviewer Agent 评估完毕。"""
    type: Literal["review_end"] = "review_end"
    sub_agent_name: str
    score: float  # 0-10
    passed: bool  # score >= 7
    feedback: str
    suggestions: Optional[List[str]] = None
    source: str = "supervisor"


class SupervisorDoneEvent(StreamEvent):
    """Supervisor 流水线执行完毕。"""
    type: Literal["supervisor_done"] = "supervisor_done"
    supervisor_session_id: str
    artifacts: Dict[str, Any]  # 所有阶段产物
    final_result: str
    source: str = "supervisor"


# Supervisor 完整流式事件联合类型
SupervisorStreamEvent = Union[
    # 来自 AgentLoop 的基础事件（带 source）
    Any,  # ThinkingEvent | TextEvent | ToolStartEvent | ToolEndEvent | ErrorEvent
    # Supervisor 新增事件
    SubAgentStartEvent,
    SubAgentEndEvent,
    ReviewStartEvent,
    ReviewEndEvent,
    SupervisorDoneEvent,
]
```

- [ ] **Step 4: 运行测试，确认通过**

```bash
cd backend && python -m pytest app/tests/unit/core/supervisor/test_events.py -v
```
Expected: PASS

- [ ] **Step 5: 提交**

```bash
cd backend && git add app/core/supervisor/events.py app/tests/unit/core/supervisor/test_events.py && git commit -m "feat(supervisor): add SupervisorStreamEvent types"
```
---

## Task 4: ToolExecutor 流式工具支持

**Files:**
- Modify: `backend/app/core/agent/tool.py`

**变更**：在 `ToolExecutor` 中新增 `execute_streaming_tool()` 方法，检测工具返回值是否为 async generator，实时 yield 事件。

- [ ] **Step 1: 添加测试**

```python
# backend/app/tests/unit/core/agent/test_tool_streaming.py
import pytest
import asyncio
from unittest.mock import MagicMock
from app.core.agent.tool import ToolExecutor
from app.core.agent.base import ToolCall


def test_execute_streaming_tool_yields_events():
    """工具返回 AsyncGenerator 时，execute_streaming_tool 实时 yield 事件。"""
    async def fake_streaming_tool(value: str):
        yield {"type": "text", "content": f"start {value}"}
        yield {"type": "text", "content": f"end {value}"}

    executor = ToolExecutor()
    # Mock ToolRegistry
    mock_tool_func = MagicMock()
    mock_tool_func.execute = fake_streaming_tool
    with pytest.MonkeyPatch.context() as mp:
        from app.core.agent import tool as tool_module
        original_get = tool_module.ToolRegistry.get
        tool_module.ToolRegistry.get = MagicMock(return_value=mock_tool_func)

        tc = ToolCall(id="tc-1", name="streaming_tool", arguments={"value": "test"})
        events = []

        async def collect():
            async for event in executor.execute_streaming_tool(tc):
                events.append(event)

        asyncio.run(collect())
        assert len(events) == 2
        assert events[0]["content"] == "start test"
        assert events[1]["content"] == "end test"

        tool_module.ToolRegistry.get = original_get


def test_execute_streaming_tool_sync_fallback():
    """工具返回同步结果时，execute_streaming_tool 转为 yield 单个 ToolEndEvent。"""
    executor = ToolExecutor()
    mock_tool_func = MagicMock()
    mock_tool_func.execute = asyncio.coroutine(lambda: {"result": "ok"})

    with pytest.MonkeyPatch.context() as mp:
        from app.core.agent import tool as tool_module
        original_get = tool_module.ToolRegistry.get
        tool_module.ToolRegistry.get = MagicMock(return_value=mock_tool_func)

        tc = ToolCall(id="tc-1", name="sync_tool", arguments={})
        events = []

        async def collect():
            async for event in executor.execute_streaming_tool(tc):
                events.append(event)

        asyncio.run(collect())
        assert len(events) == 1
        assert events[0].type == "tool_end"
        assert events[0].is_error is False

        tool_module.ToolRegistry.get = original_get
```

- [ ] **Step 2: 运行测试，确认失败**

```bash
cd backend && python -m pytest app/tests/unit/core/agent/test_tool_streaming.py -v
```
Expected: FAIL — method not found

- [ ] **Step 3: 编写实现（修改 tool.py）**

在 `ToolExecutor` 类末尾添加：

```python
# backend/app/core/agent/tool.py 新增方法

    async def execute_streaming_tool(self, tool_call: ToolCall):
        """
        执行返回 AsyncGenerator[StreamEvent] 的流式工具。

        透传所有事件，不缓冲。
        用于 call_sub_agent 等需要实时流式输出的工具。

        Args:
            tool_call: ToolCall，包含 name 和 arguments

        Yields:
            StreamEvent: 工具产生的每个事件
        """
        tool_func = self.get_tool(tool_call.name)
        if tool_func is None:
            yield ToolEndEvent(
                tool_call_id=tool_call.id,
                tool_name=tool_call.name,
                result={"error": f"Tool '{tool_call.name}' not found"},
                is_error=True,
            )
            return

        kwargs = dict(tool_call.arguments)
        if self.db is not None and "db" not in kwargs:
            kwargs["db"] = self.db

        try:
            result = await tool_func.execute(**kwargs)

            # 新工具：返回 AsyncGenerator，实时透传事件
            if hasattr(result, "__aiter__"):
                async for event in result:
                    yield event
            else:
                # 旧工具：返回同步结果，转为 ToolEndEvent
                yield ToolEndEvent(
                    tool_call_id=tool_call.id,
                    tool_name=tool_call.name,
                    result=result,
                    is_error=False,
                )
        except Exception as e:
            logger.exception(f"Tool '{tool_call.name}' streaming execution failed: {e}")
            yield ToolEndEvent(
                tool_call_id=tool_call.id,
                tool_name=tool_call.name,
                result={"error": str(e)},
                is_error=True,
            )
```

- [ ] **Step 4: 运行测试，确认通过**

```bash
cd backend && python -m pytest app/tests/unit/core/agent/test_tool_streaming.py -v
```
Expected: PASS

- [ ] **Step 5: 提交**

```bash
cd backend && git add app/core/agent/tool.py app/tests/unit/core/agent/test_tool_streaming.py && git commit -m "feat(agent): add ToolExecutor.execute_streaming_tool for async generator tools"
```
---

## Task 5: call_sub_agent 工具

**Files:**
- Modify: `backend/app/core/supervisor/tools.py`（新建）
- Tests: `backend/app/tests/unit/core/supervisor/test_tools.py`

**核心**：实现 `call_sub_agent` 工具函数。签名：
```python
async def call_sub_agent(
    sub_agent_name: str,
    task_description: str,
    context_snapshot: str,
    supervisor_context: SupervisorContext,  # ToolExecutor 注入
    db=None,
) -> AsyncGenerator[SupervisorStreamEvent, None]:
```

- [ ] **Step 1: 编写测试**

```python
# backend/app/tests/unit/core/supervisor/test_tools.py
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
import asyncio

from app.core.supervisor.context import SupervisorContext
from app.core.supervisor.session import SupervisorSession


def test_call_sub_agent_input_schema():
    """验证 call_sub_agent 工具的输入参数符合设计。"""
    from app.core.tools.registry import ToolRegistry

    tool_func = ToolRegistry.get("call_sub_agent")
    assert tool_func is not None, "call_sub_agent should be registered"
    schema = tool_func.get_schema()
    params = schema["parameters"]
    assert "sub_agent_name" in params["properties"]
    assert "task_description" in params["properties"]
    assert "context_snapshot" in params["properties"]


def test_call_reviewer_input_schema():
    """验证 call_reviewer 工具的输入参数符合设计。"""
    from app.core.tools.registry import ToolRegistry

    tool_func = ToolRegistry.get("call_reviewer")
    assert tool_func is not None, "call_reviewer should be registered"
    schema = tool_func.get_schema()
    params = schema["parameters"]
    assert "content" in params["properties"]
    assert "review_criteria" in params["properties"]


def test_get_workflow_state_input_schema():
    """验证 get_workflow_state 工具的输入参数符合设计。"""
    from app.core.tools.registry import ToolRegistry

    tool_func = ToolRegistry.get("get_workflow_state")
    assert tool_func is not None, "get_workflow_state should be registered"
```

- [ ] **Step 2: 运行测试，确认失败**

```bash
cd backend && python -m pytest app/tests/unit/core/supervisor/test_tools.py -v
```
Expected: FAIL — module not found

- [ ] **Step 3: 编写 call_sub_agent 工具实现**

```python
# backend/app/core/supervisor/tools.py
"""
Supervisor 工具：call_sub_agent / call_reviewer / get_workflow_state。
"""

import json
import logging
from typing import Any, AsyncGenerator, Dict, List, Optional
from uuid import uuid4

from app.core.agent.agent import Agent
from app.core.agent.base import AgentConfig, ToolCall
from app.core.agent.factory import create_agent
from app.core.agent.tool import ToolExecutor
from app.core.agent.base import (
    SubAgentStartEvent,
    SubAgentEndEvent,
    ToolStartEvent,
    ToolEndEvent,
    ThinkingEvent,
    TextEvent,
    DoneEvent,
    ErrorEvent,
)
from app.core.supervisor.context import SupervisorContext
from app.core.supervisor.reviewer import build_reviewer_prompt

logger = logging.getLogger(__name__)

# Supervisor 可调用的 SubAgent 名称白名单
SUB_AGENT_NAMES = {"outline_writer", "script_writer", "storyboarder"}


def _build_call_sub_agent_schema() -> Dict[str, Any]:
    return {
        "name": "call_sub_agent",
        "description": (
            "调用指定的 SubAgent 执行任务，实时返回流式事件。\n"
            "Args:\n"
            "  sub_agent_name: SubAgent 名称，可选值：outline_writer | script_writer | storyboarder\n"
            "  task_description: 给 SubAgent 的具体任务描述（包含角色定义 + 任务 + 参考产物）\n"
            "  context_snapshot: 前序 SubAgent 产物的 JSON 字符串（选择性注入上下文）\n"
            "Returns: 流式事件（SubAgentStart → Thinking/Text/ToolStart/ToolEnd → SubAgentEnd）\n"
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "sub_agent_name": {
                    "type": "string",
                    "description": "SubAgent 名称：outline_writer | script_writer | storyboarder",
                    "enum": list(SUB_AGENT_NAMES),
                },
                "task_description": {
                    "type": "string",
                    "description": "Supervisor 构造的 prompt：角色 + 具体任务 + 参考产物",
                },
                "context_snapshot": {
                    "type": "string",
                    "description": "前序产物 JSON，供 SubAgent 参考（如大纲 JSON）",
                },
            },
            "required": ["sub_agent_name", "task_description"],
        },
    }


async def call_sub_agent(
    sub_agent_name: str,
    task_description: str,
    context_snapshot: str = "",
    supervisor_context: Optional[SupervisorContext] = None,
    db=None,
) -> AsyncGenerator[SubAgentStartEvent | SubAgentEndEvent, None]:
    """
    调用指定的 SubAgent 执行任务，实时 yield 所有流式事件。

    设计要点：
    - SubAgent 不访问 supervisor_context，只通过 task_description 接收必要数据
    - session_id 格式：sub-{agent_name}-{uuid4()[:8]}
    - 流式事件实时透传到 SSE
    """
    if sub_agent_name not in SUB_AGENT_NAMES:
        yield SubAgentEndEvent(
            sub_agent_name=sub_agent_name,
            session_id="",
            result={},
        )
        return

    sub_session_id = f"sub-{sub_agent_name}-{str(uuid4())[:8]}"

    # 构建 SubAgent 的 prompt
    # task_description 本身已由 Supervisor 构造好，直接作为 system prompt
    sub_prompt = task_description
    if context_snapshot:
        sub_prompt = f"{task_description}\n\n## 参考上下文\n{context_snapshot}"

    # 创建 SubAgent 实例
    sub_agent = create_agent(
        agent_name=sub_agent_name,
        session_id=sub_session_id,
        prompt=sub_prompt,
        model="gemini-3-flash-preview",
        max_loop=20,
        persist="redis",
    )

    # 记录 session 关联
    if supervisor_context is not None:
        supervisor_context.sub_agent_sessions[sub_agent_name] = sub_session_id

    logger.info(
        f"[call_sub_agent] starting sub_agent={sub_agent_name}, "
        f"session={sub_session_id}"
    )

    # yield SubAgent 开始事件
    yield SubAgentStartEvent(
        sub_agent_name=sub_agent_name,
        session_id=sub_session_id,
        task_description=task_description,
    )

    # 流式执行 SubAgent
    try:
        accumulated_content = ""
        accumulated_result = {}

        async for event in sub_agent.stream(initial_input=""):
            if isinstance(event, ThinkingEvent):
                yield ThinkingEvent(content=event.content, source=sub_agent_name)
            elif isinstance(event, TextEvent):
                accumulated_content += event.content
                yield TextEvent(content=event.content, source=sub_agent_name)
            elif isinstance(event, ToolStartEvent):
                yield ToolStartEvent(
                    tool_call_id=event.tool_call_id,
                    tool_name=event.tool_name,
                    arguments=event.arguments,
                    source=sub_agent_name,
                )
            elif isinstance(event, ToolEndEvent):
                yield ToolEndEvent(
                    tool_call_id=event.tool_call_id,
                    tool_name=event.tool_name,
                    result=event.result,
                    is_error=event.is_error,
                    source=sub_agent_name,
                )
            elif isinstance(event, DoneEvent):
                accumulated_result = {
                    "schema_data": event.result.schema_data,
                    "raw_output": event.result.raw_output,
                    "loop_count": event.result.loop_count,
                }
                # 保存产物到 artifacts
                if supervisor_context is not None:
                    supervisor_context.artifacts[sub_agent_name] = (
                        event.result.schema_data or event.result.raw_output
                    )
                logger.info(
                    f"[call_sub_agent] completed sub_agent={sub_agent_name}, "
                    f"loop_count={event.result.loop_count}"
                )
    except Exception as e:
        logger.exception(f"[call_sub_agent] error in sub_agent={sub_agent_name}: {e}")
        yield ErrorEvent(error=str(e), source=sub_agent_name)
        accumulated_result = {"error": str(e)}

    # yield SubAgent 结束事件
    yield SubAgentEndEvent(
        sub_agent_name=sub_agent_name,
        session_id=sub_session_id,
        result=accumulated_result,
    )
```

- [ ] **Step 4: 运行测试，确认通过**

```bash
cd backend && python -m pytest app/tests/unit/core/supervisor/test_tools.py -v
```
Expected: PASS

- [ ] **Step 5: 提交**

```bash
cd backend && git add app/core/supervisor/tools.py app/tests/unit/core/supervisor/test_tools.py && git commit -m "feat(supervisor): implement call_sub_agent streaming tool"
```
---

## Task 6: call_reviewer + get_workflow_state 工具

**Files:**
- Modify: `backend/app/core/supervisor/tools.py`

- [ ] **Step 1: 添加工具注册和 get_workflow_state 实现**

在 `tools.py` 末尾追加：

```python
# ----------------------------------------------------------------------
# call_reviewer 工具
# ----------------------------------------------------------------------


def _build_call_reviewer_schema() -> Dict[str, Any]:
    return {
        "name": "call_reviewer",
        "description": (
            "调用 Reviewer Agent 评估内容质量。\n"
            "Args:\n"
            "  content: 需要评估的内容（文本或 JSON）\n"
            "  review_criteria: 评估维度列表，如：情感张力 | 结构完整性 | 分镜合理性\n"
            "Returns: {score: 0-10, passed: bool, feedback: str, suggestions: []}\n"
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "content": {"type": "string", "description": "待评估内容"},
                "review_criteria": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "评估维度列表",
                },
            },
            "required": ["content", "review_criteria"],
        },
    }


async def call_reviewer(
    content: str,
    review_criteria: List[str],
    supervisor_context: Optional[SupervisorContext] = None,
    db=None,
) -> Dict[str, Any]:
    """
    调用 Reviewer Agent 评估内容质量。

    Reviewer 是一个标准 Agent，封装在此函数中。
    返回 {score, passed, feedback, suggestions}。
    """
    reviewer_session_id = f"reviewer-{str(uuid4())[:8]}"
    reviewer_prompt = build_reviewer_prompt(content, review_criteria)

    reviewer_agent = create_agent(
        agent_name="reviewer",
        session_id=reviewer_session_id,
        prompt=reviewer_prompt,
        model="gemini-3-flash-preview",
        max_loop=10,
        persist="redis",
    )

    try:
        result = await reviewer_agent.run(initial_input="")
        raw = result.raw_output or ""

        # 尝试从 raw_output 中解析 score / passed / feedback
        # 约定 Reviewer 返回格式：JSON {score, passed, feedback, suggestions}
        import re

        json_match = re.search(r"\{[\s\S]+\}", raw)
        if json_match:
            review_data = json.loads(json_match.group())
        else:
            review_data = {
                "score": 7.0,
                "passed": True,
                "feedback": raw,
                "suggestions": [],
            }

        score = float(review_data.get("score", 7.0))
        passed = review_data.get("passed", score >= 7.0)

        # 记录到 review_history
        if supervisor_context is not None:
            supervisor_context.review_history.append({
                "score": score,
                "passed": passed,
                "feedback": review_data.get("feedback", ""),
            })

        return {
            "score": score,
            "passed": passed,
            "feedback": review_data.get("feedback", ""),
            "suggestions": review_data.get("suggestions", []),
        }
    except Exception as e:
        logger.exception(f"[call_reviewer] error: {e}")
        return {
            "score": 0.0,
            "passed": False,
            "feedback": f"Reviewer 执行失败：{str(e)}",
            "suggestions": [],
        }


# ----------------------------------------------------------------------
# get_workflow_state 工具
# ----------------------------------------------------------------------


def _build_get_workflow_state_schema() -> Dict[str, Any]:
    return {
        "name": "get_workflow_state",
        "description": (
            "查询当前流水线状态和已有产物。\n"
            "Returns: {current_phase, artifacts, review_history}\n"
        ),
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    }


async def get_workflow_state(
    supervisor_context: SupervisorContext,
) -> Dict[str, Any]:
    """
    查询当前流水线状态。

    供 Supervisor Agent（LLM）做决策参考。
    注意：此工具是给 Supervisor 用的，不是给 SubAgent 用的。
    """
    return {
        "current_phase": supervisor_context.current_phase,
        "artifacts": supervisor_context.artifacts,
        "review_history": supervisor_context.review_history,
        "sub_agent_sessions": supervisor_context.sub_agent_sessions,
    }


# ----------------------------------------------------------------------
# 工具注册（供 factory.py 调用以获取 schema 列表）
# ----------------------------------------------------------------------


def get_supervisor_tool_schemas() -> List[Dict[str, Any]]:
    """返回所有 Supervisor 工具的 schema 列表。"""
    return [
        _build_call_sub_agent_schema(),
        _build_call_reviewer_schema(),
        _build_get_workflow_state_schema(),
    ]
```

- [ ] **Step 2: 注册工具到 ToolRegistry（临时方案，在 supervisor_tools.py 中导入）**

```python
# backend/app/core/supervisor/__init__.py
"""
Supervisor 模块。
"""
from app.core.supervisor.context import SupervisorContext
from app.core.supervisor.session import SupervisorSession
from app.core.supervisor.events import SupervisorStreamEvent
from app.core.supervisor.factory import create_supervisor

__all__ = [
    "SupervisorContext",
    "SupervisorSession",
    "SupervisorStreamEvent",
    "create_supervisor",
]
```

- [ ] **Step 3: 提交**

```bash
cd backend && git add app/core/supervisor/tools.py app/core/supervisor/__init__.py && git commit -m "feat(supervisor): add call_reviewer and get_workflow_state tools"
```
---

## Task 7: Reviewer Agent 配置

**Files:**
- Create: `backend/app/core/supervisor/reviewer.py`
- Tests: `backend/app/tests/unit/core/supervisor/test_reviewer.py`

- [ ] **Step 1: 编写测试**

```python
# backend/app/tests/unit/core/supervisor/test_reviewer.py
import pytest
from app.core.supervisor.reviewer import build_reviewer_prompt, DEFAULT_REVIEWER_SYSTEM_PROMPT


def test_build_reviewer_prompt_includes_content():
    prompt = build_reviewer_prompt(
        content="这是一个测试剧本",
        review_criteria=["情感张力", "结构完整性"],
    )
    assert "这是一个测试剧本" in prompt
    assert "情感张力" in prompt
    assert "结构完整性" in prompt


def test_build_reviewer_prompt_contains_scoring_instruction():
    prompt = build_reviewer_prompt(
        content="测试内容",
        review_criteria=["创意性"],
    )
    assert "score" in prompt.lower()
    assert "passed" in prompt.lower()


def test_default_reviewer_prompt_not_empty():
    assert len(DEFAULT_REVIEWER_SYSTEM_PROMPT) > 0
```

- [ ] **Step 2: 运行测试，确认失败**

```bash
cd backend && python -m pytest app/tests/unit/core/supervisor/test_reviewer.py -v
```
Expected: FAIL — module not found

- [ ] **Step 3: 编写实现**

```python
# backend/app/core/supervisor/reviewer.py
"""
Reviewer Agent 的 prompt 配置。

Reviewer 是一个独立的评估 Agent，通过 call_reviewer 工具调用。
"""

from typing import List


DEFAULT_REVIEWER_SYSTEM_PROMPT = """你是一个专业的影视内容评审专家。你的职责是客观评估剧本/大纲/分镜的质量。

评审要求：
1. 严格、诚实、不溢美
2. 指出具体问题，不说空话
3. 给出可操作的改进建议

评分标准：
- 8-10 分：优秀，几乎无需修改
- 6-7 分：良好，有少量改进空间
- 4-5 分：一般，需要较大修改
- 0-3 分：不合格，需要重新设计

输出格式（必须返回 JSON）：
{
    "score": 8.5,
    "passed": true,
    "feedback": "具体反馈，不超过200字",
    "suggestions": ["建议1", "建议2"]
}
"""


def build_reviewer_prompt(content: str, review_criteria: List[str]) -> str:
    """
    构建 Reviewer Agent 的完整 system prompt。

    Args:
        content: 待评估的内容
        review_criteria: 评估维度列表

    Returns:
        完整的 system prompt 字符串
    """
    criteria_str = "\n".join(f"  - {c}" for c in review_criteria)
    return f"""{DEFAULT_REVIEWER_SYSTEM_PROMPT}

## 待评估内容
{content}

## 评审维度
请重点评估以下维度：
{criteria_str}

请返回 JSON 格式的评审结果。
"""
```

- [ ] **Step 4: 运行测试，确认通过**

```bash
cd backend && python -m pytest app/tests/unit/core/supervisor/test_reviewer.py -v
```
Expected: PASS

- [ ] **Step 5: 提交**

```bash
cd backend && git add app/core/supervisor/reviewer.py app/tests/unit/core/supervisor/test_reviewer.py && git commit -m "feat(supervisor): add Reviewer Agent prompt configuration"
```
---

## Task 8: SupervisorAgent 核心类

**Files:**
- Create: `backend/app/core/supervisor/supervisor.py`
- Tests: `backend/app/tests/unit/core/supervisor/test_supervisor.py`

- [ ] **Step 1: 编写测试**

```python
# backend/app/tests/unit/core/supervisor/test_supervisor.py
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from app.core.supervisor.supervisor import SupervisorAgent
from app.core.supervisor.context import SupervisorContext
from app.core.supervisor.session import SupervisorSession


def test_supervisor_agent_holds_context():
    ctx = SupervisorContext(
        supervisor_session_id="sv-test",
        user_request="测试需求",
    )
    session = SupervisorSession("sv-test")

    # SupervisorAgent 构造时不实际创建 agent，只验证属性
    with patch("app.core.supervisor.supervisor.create_agent") as mock_create:
        mock_create.return_value = MagicMock()
        agent = SupervisorAgent(
            supervisor_session_id="sv-test",
            user_request="测试需求",
            sub_agent_configs={},
            middlewares=[],
            persist=None,
        )
        assert agent.context.user_request == "测试需求"
        assert agent.context.supervisor_session_id == "sv-test"
        assert agent.session.supervisor_session_id == "sv-test"


def test_supervisor_system_prompt_contains_tools():
    with patch("app.core.supervisor.supervisor.create_agent") as mock_create:
        mock_create.return_value = MagicMock()
        agent = SupervisorAgent(
            supervisor_session_id="sv-test",
            user_request="测试需求",
            sub_agent_configs={},
            middlewares=[],
            persist=None,
        )
        prompt = agent._build_system_prompt()
        assert "call_sub_agent" in prompt
        assert "call_reviewer" in prompt
        assert "get_workflow_state" in prompt
        assert "测试需求" in prompt
```

- [ ] **Step 2: 运行测试，确认失败**

```bash
cd backend && python -m pytest app/tests/unit/core/supervisor/test_supervisor.py -v
```
Expected: FAIL — module not found

- [ ] **Step 3: 编写实现**

```python
# backend/app/core/supervisor/supervisor.py
"""
SupervisorAgent — 视频生成流水线的元 Agent。
"""

import json
import logging
from typing import Any, AsyncGenerator, Dict, List, Optional

from app.core.agent.agent import Agent
from app.core.agent.base import AgentConfig, AgentResult
from app.core.agent.factory import create_agent
from app.core.agent.persist.base import PersistStrategy
from app.core.middleware.chain import AgentMiddleware
from app.core.supervisor.context import SupervisorContext
from app.core.supervisor.events import SupervisorStreamEvent
from app.core.supervisor.session import SupervisorSession
from app.core.supervisor.tools import get_supervisor_tool_schemas

logger = logging.getLogger(__name__)

# Supervisor Agent 的 system prompt 模板
SUPERVISOR_SYSTEM_PROMPT_TEMPLATE = """你是一个视频生成流水线的 Supervisor Agent。你的职责是：

## 可用工具
- call_sub_agent(sub_agent_name, task_description, context_snapshot)
- call_reviewer(content, review_criteria)
- get_workflow_state()

## 流水线阶段
1. outline_writer → 生成视频大纲（JSON Schema: OutlineSchema）
2. script_writer → 基于大纲创作剧本（JSON Schema: ScriptSchema）
3. storyboarder → 生成分镜组（JSON Schema: StoryboardSchema）

## 工作原则
- 先理解用户需求，制定流水线计划
- 每个 SubAgent 调用后，用 Reviewer 评估结果（threshold = 7/10）
- 评估不通过时，说明原因并决定：重试同 Agent 或调整策略
- 流水线完成后，汇总所有产物并返回最终结果
- 遇到错误时，尝试恢复或换备选方案，不要轻易放弃
- 重要：不要让用户等待太久，每轮决策尽量简洁

## Supervisor 工具说明

### call_sub_agent
调用 SubAgent 执行任务：
- sub_agent_name: outline_writer | script_writer | storyboarder
- task_description: 角色定义 + 具体任务描述
- context_snapshot: 前序产物 JSON（选择性注入）

### call_reviewer
评估内容质量：
- content: 待评估内容
- review_criteria: 评估维度列表
- 返回: {score, passed, feedback, suggestions}

### get_workflow_state
查询当前流水线状态（ Supervisor 决策参考）。

## 当前用户需求
{user_request}
"""


class SupervisorAgent:
    """
    Supervisor Agent。

    组合标准 Agent 能力，复用 run()/stream() 模式。
    差异点：
    - 有自己的 system prompt（流水线描述 + 工具说明）
    - 持有 SupervisorContext（工作内存，SubAgent 无法访问）
    - 持有 SupervisorSession（session 关联管理）
    - 工具集为 {call_sub_agent, call_reviewer, get_workflow_state}
    - stream() 将 SubAgent 事件实时透传到 SSE
    """

    def __init__(
        self,
        supervisor_session_id: str,
        user_request: str,
        sub_agent_configs: Dict[str, Any],
        middlewares: List[AgentMiddleware],
        persist: Optional[PersistStrategy],
        model: str = "gemini-3-flash-preview",
        max_loop: int = 30,
    ):
        self.supervisor_session_id = supervisor_session_id
        self.context = SupervisorContext(
            supervisor_session_id=supervisor_session_id,
            user_request=user_request,
        )
        self.session = SupervisorSession(supervisor_session_id)
        self._sub_agent_configs = sub_agent_configs

        # 构建 Supervisor 工具 schema
        tool_schemas = get_supervisor_tool_schemas()

        # 将 supervisor_context 作为全局变量传入 tools（通过闭包）
        # 注意：ToolExecutor 会通过 kwargs 注入 supervisor_context
        # 这里我们将其存放在 self._tool_ctx 上，在 factory 层传入
        self._tool_ctx = {
            "supervisor_context": self.context,
        }

        # 创建底层的标准 Agent
        self._agent = create_agent(
            agent_name="supervisor",
            session_id=supervisor_session_id,
            prompt=self._build_system_prompt(),
            tools=tool_schemas,
            max_loop=max_loop,
            persist=persist,
            middlewares=middlewares,
        )

        logger.info(
            f"[SupervisorAgent] created supervisor_session={supervisor_session_id}, "
            f"max_loop={max_loop}"
        )

    def _build_system_prompt(self) -> str:
        return SUPERVISOR_SYSTEM_PROMPT_TEMPLATE.format(
            user_request=self.context.user_request,
        )

    async def run(self, initial_input: str) -> AgentResult:
        """
        非流式执行，返回流水线最终结果。

        Supervisor 不使用 run()，流水线推荐使用 stream()。
        此方法用于简单场景。
        """
        return await self._agent.run(initial_input)

    async def stream(
        self,
        initial_input: str,
    ) -> AsyncGenerator[SupervisorStreamEvent, None]:
        """
        流式执行，yield SupervisorStreamEvent。

        事件透传逻辑：
        - Supervisor 的 Thinking/Text 事件：透传（source = "supervisor"）
        - ToolStart/ToolEnd 事件：
          - 若 tool_name 是 call_sub_agent → SubAgent 的事件已在工具内部 yield
          - 其他工具 → 透传（source = "supervisor"）
        - SubAgentStart/SubAgentEnd 事件：透传（工具内部 yield）
        - SupervisorDoneEvent：最后 yield
        """
        accumulated_result = ""
        final_artifacts = {}

        try:
            async for event in self._agent.stream(initial_input):
                # 为基础事件统一标记 source
                if hasattr(event, "source") and not getattr(event, "source", None):
                    event.source = "supervisor"

                # 累积 Supervisor 最终文本
                if hasattr(event, "content") and hasattr(event, "type") and event.type == "text":
                    accumulated_result += event.content

                yield event

            # 流水线结束，yield SupervisorDoneEvent
            final_artifacts = dict(self.context.artifacts)
            yield type("SupervisorDoneEvent", (), {
                "type": "supervisor_done",
                "supervisor_session_id": self.supervisor_session_id,
                "artifacts": final_artifacts,
                "final_result": accumulated_result or "流水线执行完毕",
                "source": "supervisor",
            })()

        except Exception as e:
            logger.exception(f"[SupervisorAgent] stream error: {e}")
            yield type("ErrorEvent", (), {
                "type": "error",
                "error": str(e),
                "source": "supervisor",
            })()
            # 最后也 yield DoneEvent
            yield type("SupervisorDoneEvent", (), {
                "type": "supervisor_done",
                "supervisor_session_id": self.supervisor_session_id,
                "artifacts": dict(self.context.artifacts),
                "final_result": f"执行出错：{str(e)}",
                "source": "supervisor",
            })()
```

- [ ] **Step 4: 运行测试，确认通过**

```bash
cd backend && python -m pytest app/tests/unit/core/supervisor/test_supervisor.py -v
```
Expected: PASS

- [ ] **Step 5: 提交**

```bash
cd backend && git add app/core/supervisor/supervisor.py app/tests/unit/core/supervisor/test_supervisor.py && git commit -m "feat(supervisor): add SupervisorAgent core class"
```
---

## Task 9: create_supervisor() 工厂

**Files:**
- Create: `backend/app/core/supervisor/factory.py`
- Tests: `backend/app/tests/unit/core/supervisor/test_factory.py`

- [ ] **Step 1: 编写测试**

```python
# backend/app/tests/unit/core/supervisor/test_factory.py
import pytest
from unittest.mock import patch
from app.core.supervisor.factory import create_supervisor


def test_create_supervisor_returns_supervisor_agent():
    with patch("app.core.supervisor.factory.SupervisorAgent") as mock_agent_cls:
        mock_instance = mock_agent_cls.return_value
        supervisor = create_supervisor(user_request="生成一个科幻短片")
        assert supervisor is not None
        mock_agent_cls.assert_called_once()


def test_create_supervisor_assigns_session_id():
    with patch("app.core.supervisor.factory.SupervisorAgent") as mock_agent_cls:
        mock_instance = mock_agent_cls.return_value
        supervisor = create_supervisor(user_request="测试需求")
        call_kwargs = mock_agent_cls.call_args.kwargs
        assert "supervisor_session_id" in call_kwargs
        assert call_kwargs["supervisor_session_id"].startswith("sv-")


def test_create_supervisor_passes_user_request():
    with patch("app.core.supervisor.factory.SupervisorAgent") as mock_agent_cls:
        mock_instance = mock_agent_cls.return_value
        supervisor = create_supervisor(user_request="我的科幻短片剧本")
        call_kwargs = mock_agent_cls.call_args.kwargs
        assert call_kwargs["user_request"] == "我的科幻短片剧本"
```

- [ ] **Step 2: 运行测试，确认失败**

```bash
cd backend && python -m pytest app/tests/unit/core/supervisor/test_factory.py -v
```
Expected: FAIL — module not found

- [ ] **Step 3: 编写实现**

```python
# backend/app/core/supervisor/factory.py
"""
Supervisor Agent 工厂函数。
"""

import logging
from typing import Any, Dict, List, Optional
from uuid import uuid4

from app.core.agent.persist.base import PersistStrategy
from app.core.agent.persist.redis_strategy import RedisPersistStrategy
from app.core.agent.persist import PersistArg
from app.core.middleware.chain import AgentMiddleware
from app.core.supervisor.supervisor import SupervisorAgent

logger = logging.getLogger(__name__)


def _resolve_persist(persist: PersistArg) -> Optional[PersistStrategy]:
    if persist is None:
        return None
    if isinstance(persist, PersistStrategy):
        return persist
    if persist == "redis":
        return RedisPersistStrategy()
    raise ValueError(
        f"未知的 persist 参数：{persist!r}，可选值：'redis' | PersistStrategy 实例 | None"
    )


def create_supervisor(
    user_request: str,
    *,
    supervisor_name: str = "supervisor",
    model: str = "gemini-3-flash-preview",
    max_loop: int = 30,
    persist: PersistArg = "redis",
    middlewares: Optional[List[AgentMiddleware]] = None,
    sub_agent_configs: Optional[Dict[str, Any]] = None,
) -> SupervisorAgent:
    """
    创建 SupervisorAgent 实例。

    Args:
        user_request: 用户原始需求
        supervisor_name: Supervisor 名称（默认 "supervisor"）
        model: LLM 模型（默认 gemini-3-flash-preview）
        max_loop: 最大循环次数（默认 30，Supervisor 需要更多决策轮次）
        persist: 持久化策略（默认 "redis"）
        middlewares: 中间件列表
        sub_agent_configs: SubAgent 配置映射（预留，未来从 DB/Skill 加载）

    Returns:
        SupervisorAgent 实例
    """
    supervisor_session_id = f"sv-{uuid4()}"
    persist_strategy = _resolve_persist(persist)

    logger.info(
        f"[create_supervisor] supervisor_session={supervisor_session_id}, "
        f"user_request={user_request[:50]}..., persist={persist}"
    )

    return SupervisorAgent(
        supervisor_session_id=supervisor_session_id,
        user_request=user_request,
        sub_agent_configs=sub_agent_configs or {},
        middlewares=middlewares or [],
        persist=persist_strategy,
        model=model,
        max_loop=max_loop,
    )
```

- [ ] **Step 4: 运行测试，确认通过**

```bash
cd backend && python -m pytest app/tests/unit/core/supervisor/test_factory.py -v
```
Expected: PASS

- [ ] **Step 5: 提交**

```bash
cd backend && git add app/core/supervisor/factory.py app/tests/unit/core/supervisor/test_factory.py && git commit -m "feat(supervisor): add create_supervisor factory"
```
---

## Task 10: 工具注册入口

**Files:**
- Create: `backend/app/core/tools/supervisor_tools.py`

- [ ] **Step 1: 创建文件**

```python
# backend/app/core/tools/supervisor_tools.py
"""
Supervisor 工具注册入口。

通过 import 触发 @register_tool 装饰器，将工具注册到 ToolRegistry。
"""

from app.core.supervisor.tools import call_sub_agent, call_reviewer, get_workflow_state

# 以下 import 仅用于触发 @register_tool 装饰器注册
# 实际工具在 SupervisorAgent._agent.stream() 中通过 ToolExecutor 执行
_imported = (call_sub_agent, call_reviewer, get_workflow_state)

__all__ = ["_imported"]
```

- [ ] **Step 2: 修改 tools/__init__.py 导入**

在 `backend/app/core/tools/__init__.py` 的 `__all__` 列表中添加：
```python
"supervisor_tools",
```

并在文件顶部（`from app.core.tools.builtin import load_skill, load_skill_lite` 之后）添加：
```python
from app.core.tools import supervisor_tools  # noqa: F401 — 触发 Supervisor 工具注册
```

- [ ] **Step 3: 验证工具已注册**

```bash
cd backend && python -c "from app.core.tools.registry import ToolRegistry; print(ToolRegistry.list_tools())"
```
Expected: 输出中包含 `call_sub_agent`, `call_reviewer`, `get_workflow_state`

- [ ] **Step 4: 提交**

```bash
cd backend && git add app/core/tools/supervisor_tools.py app/core/tools/__init__.py && git commit -m "feat(supervisor): register supervisor tools in ToolRegistry"
```
---

## Task 11: API 路由集成

**Files:**
- Create: `backend/app/api/supervisor.py`
- Modify: `backend/app/main.py`（或 router 注册）

**实现 SSE 流式接口**：`POST /supervisor/stream`

- [ ] **Step 1: 编写路由**

```python
# backend/app/api/supervisor.py
"""
Supervisor API 路由。
"""

import json
import logging
from typing import Optional

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.core.agent.persist import PersistArg
from app.core.middleware.chain import AgentMiddleware
from app.core.supervisor.factory import create_supervisor
from app.core.supervisor.events import (
    SubAgentStartEvent,
    SubAgentEndEvent,
    ReviewStartEvent,
    ReviewEndEvent,
    SupervisorDoneEvent,
)
from app.core.agent.base import (
    ThinkingEvent,
    TextEvent,
    ToolStartEvent,
    ToolEndEvent,
    DoneEvent,
    ErrorEvent,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/supervisor", tags=["supervisor"])


class SupervisorStreamRequest(BaseModel):
    user_request: str
    model: Optional[str] = "gemini-3-flash-preview"
    max_loop: Optional[int] = 30
    persist: PersistArg = "redis"
    middlewares: Optional[list] = None


@router.post("/stream")
async def supervisor_stream(request: SupervisorStreamRequest):
    """
    启动 Supervisor 流水线，流式返回 SSE 事件。

    请求体：
    {
        "user_request": "帮我生成一个科幻短片的剧本，时长2分钟",
        "model": "gemini-3-flash-preview"
    }
    """
    supervisor = create_supervisor(
        user_request=request.user_request,
        model=request.model or "gemini-3-flash-preview",
        max_loop=request.max_loop or 30,
        persist=request.persist,
        middlewares=request.middlewares or [],
    )

    async def event_generator():
        try:
            async for event in supervisor.stream(request.user_request):
                # 将 Pydantic 模型序列化为 SSE 格式
                event_data = {
                    **{"type": event.type} if hasattr(event, "type") else {},
                    **{k: v for k, v in event.model_dump().items() if k != "type"},
                }
                yield f"data: {json.dumps(event_data, ensure_ascii=False)}\n\n"
        except Exception as e:
            logger.exception(f"[supervisor/stream] SSE error: {e}")
            yield f"data: {json.dumps({'type': 'error', 'error': str(e)})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
```

- [ ] **Step 2: 注册路由（在 main.py 或 router 入口）**

```python
# backend/app/api/__init__.py 或 main.py
from app.api.supervisor import router as supervisor_router

# 如果使用统一 router：
# app.include_router(supervisor_router)
```

- [ ] **Step 3: 提交**

```bash
cd backend && git add app/api/supervisor.py && git commit -m "feat(api): add POST /supervisor/stream SSE endpoint"
```
---

## Task 12: 新增 `supervisor_workflows` 表

**Files:**
- Modify: `backend/app/core/agent/persist/models.py`（新增 SupervisorWorkflow ORM 模型）
- Tests: `backend/app/tests/unit/core/supervisor/test_workflow.py`

**目标**：存储流水线元信息，支持断点续跑和多会话关联查询。

- [ ] **Step 1: 编写测试**

```python
# backend/app/tests/unit/core/supervisor/test_workflow.py
import pytest
from datetime import datetime, timezone
from app.core.agent.persist.models import SupervisorWorkflow


def test_supervisor_workflow_defaults():
    wf = SupervisorWorkflow(
        supervisor_session_id="sv-abc123",
        user_request="生成科幻短片剧本",
    )
    assert wf.supervisor_session_id == "sv-abc123"
    assert wf.current_phase == "init"
    assert wf.artifacts == {}
    assert wf.review_history == []
    assert wf.status == "running"


def test_supervisor_workflow_update_artifacts():
    wf = SupervisorWorkflow(
        supervisor_session_id="sv-abc123",
        user_request="生成科幻短片剧本",
    )
    wf.artifacts["outline"] = {"title": "星际穿越", "scenes": 5}
    assert wf.artifacts["outline"]["title"] == "星际穿越"
    wf.current_phase = "outline"
    assert wf.current_phase == "outline"


def test_supervisor_workflow_status_transitions():
    wf = SupervisorWorkflow(
        supervisor_session_id="sv-abc123",
        user_request="生成科幻短片剧本",
    )
    assert wf.status == "running"
    wf.status = "completed"
    assert wf.status == "completed"
    wf.status = "failed"
    assert wf.status == "failed"
```

- [ ] **Step 2: 运行测试，确认失败**

```bash
cd backend && python -m pytest app/tests/unit/core/supervisor/test_workflow.py -v
```
Expected: FAIL — model not found

- [ ] **Step 3: 编写 ORM 模型（在 models.py 末尾追加）**

```python
# backend/app/core/agent/persist/models.py 末尾追加

class SupervisorWorkflow(Base):
    """
    流水线元信息表。

    记录每个 Supervisor session 的流水线状态：
    - 当前阶段、产物快照、评估历史
    - 支持断点续跑和多会话关联查询

    关联关系：
    - 通过 supervisor_session_id 与 agent_messages.supervisor_session_id 关联
    - 各 SubAgent 的消息通过 supervisor_session_id 查到对应的完整流水线上下文
    """

    __tablename__ = "supervisor_workflows"

    supervisor_session_id: Mapped[str] = mapped_column(
        String(100),
        primary_key=True,
        comment="Supervisor session ID（与 agent_messages.supervisor_session_id 对应）",
    )
    user_request: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="用户原始需求",
    )
    current_phase: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="init",
        comment="当前阶段：init | outline | script | storyboard | review | done",
    )
    artifacts: Mapped[Optional[dict]] = mapped_column(
        JSON,
        nullable=True,
        comment="各阶段产物 JSON：{outline: {...}, script: {...}, storyboard: {...}}",
    )
    review_history: Mapped[Optional[list]] = mapped_column(
        JSON,
        nullable=True,
        comment="评估历史：[{\"agent\": \"outline_writer\", \"score\": 8.5, \"passed\": true}, ...]",
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="running",
        comment="流水线状态：running | completed | failed",
    )
```

- [ ] **Step 4: 运行测试，确认通过**

```bash
cd backend && python -m pytest app/tests/unit/core/supervisor/test_workflow.py -v
```
Expected: PASS

- [ ] **Step 5: 提交**

```bash
cd backend && git add app/core/agent/persist/models.py app/tests/unit/core/supervisor/test_workflow.py && git commit -m "feat(db): add supervisor_workflows table for pipeline metadata"
```
---

## Task 13: `agent_messages` 表新增 `supervisor_session_id` 字段

**Files:**
- Modify: `backend/app/core/agent/persist/models.py`（AgentMessageRecord 新增字段）
- Modify: `backend/app/core/agent/persist/db_strategy.py`（DBPersistStrategy 支持新字段）
- Tests: `backend/app/tests/unit/core/agent/test_db_persist.py`

**目标**：SubAgent 的消息通过 `supervisor_session_id` 关联到 Supervisor，支持"查询某 Supervisor 下所有 SubAgent 消息"的查询。

- [ ] **Step 1: 编写测试**

```python
# backend/app/tests/unit/core/agent/test_db_persist.py
import pytest
from unittest.mock import AsyncMock, MagicMock
from app.core.agent.persist.db_strategy import DBPersistStrategy


def test_append_message_includes_supervisor_session_id():
    """验证 append_message 接收并写入 supervisor_session_id 字段。"""
    mock_db = AsyncMock()
    mock_db.commit = AsyncMock()

    strategy = DBPersistStrategy(db=mock_db)

    import asyncio
    asyncio.get_event_loop().run_until_complete(
        strategy.append_message(
            session_id="sub-outline-001",
            request_id="req-001",
            agent_name="outline_writer",
            role="assistant",
            content="大纲已生成",
            seq=0,
            supervisor_session_id="sv-abc123",  # 新增字段
        )
    )

    # 验证 self.db.add 被调用，且 record 包含新字段
    call_args = mock_db.add.call_args
    record = call_args[0][0]
    assert hasattr(record, "supervisor_session_id")
    assert record.supervisor_session_id == "sv-abc123"
```

- [ ] **Step 2: 运行测试，确认失败**

```bash
cd backend && python -m pytest app/tests/unit/core/agent/test_db_persist.py -v
```
Expected: FAIL — field not found

- [ ] **Step 3: 修改 AgentMessageRecord（models.py）**

在 `agent_messages` 表定义中，在 `agent_name` 字段后追加：

```python
# backend/app/core/agent/persist/models.py
# AgentMessageRecord 中，在 agent_name 字段后追加：

    supervisor_session_id: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        index=True,
        comment="所属 Supervisor session ID（SubAgent 消息关联到 Supervisor）",
    )
```

- [ ] **Step 4: 修改 DBPersistStrategy.append_message()（db_strategy.py）**

```python
# backend/app/core/agent/persist/db_strategy.py
# append_message() 方法签名新增参数：

    async def append_message(
        self,
        session_id: str,
        request_id: str,
        agent_name: str,
        role: str,
        content: str,
        seq: int,
        *,
        tool_call_id: Optional[str] = None,
        tool_name: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        usage: Optional[Dict[str, Any]] = None,
        supervisor_session_id: Optional[str] = None,  # 新增
    ) -> None:

        record = AgentMessageRecord(
            session_id=session_id,
            request_id=request_id,
            agent_name=agent_name,
            role=role,
            content=content,
            seq=seq,
            tool_call_id=tool_call_id,
            tool_name=tool_name,
            extra_metadata=metadata,
            usage=usage,
            supervisor_session_id=supervisor_session_id,  # 新增
        )
        self.db.add(record)
        await self.db.commit()
```

- [ ] **Step 5: 运行测试，确认通过**

```bash
cd backend && python -m pytest app/tests/unit/core/agent/test_db_persist.py -v
```
Expected: PASS

- [ ] **Step 6: 提交**

```bash
cd backend && git add app/core/agent/persist/models.py app/core/agent/persist/db_strategy.py app/tests/unit/core/agent/test_db_persist.py && git commit -m "feat(db): add supervisor_session_id to agent_messages table"
```
---

## Task 14: SupervisorWorkflow Service

**Files:**
- Create: `backend/app/core/supervisor/workflow_service.py`
- Tests: `backend/app/tests/unit/core/supervisor/test_workflow_service.py`

**目标**：封装流水线元信息的 DB 读写操作，供 `call_sub_agent` 工具调用。

- [ ] **Step 1: 编写测试**

```python
# backend/app/tests/unit/core/supervisor/test_workflow_service.py
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


def test_create_workflow():
    with patch("app.core.supervisor.workflow_service.SupervisorWorkflow") as mock_model:
        from app.core.supervisor.workflow_service import SupervisorWorkflowService

        mock_db = AsyncMock()
        service = SupervisorWorkflowService(db=mock_db)

        import asyncio
        asyncio.get_event_loop().run_until_complete(
            service.create_workflow(
                supervisor_session_id="sv-abc123",
                user_request="生成科幻短片剧本",
            )
        )
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()


def test_update_artifacts():
    with patch("app.core.supervisor.workflow_service.SupervisorWorkflow") as mock_model:
        from app.core.supervisor.workflow_service import SupervisorWorkflowService

        mock_db = AsyncMock()
        mock_db.execute = AsyncMock()

        # Mock 查到的 workflow
        mock_wf = MagicMock()
        mock_wf.artifacts = {}
        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = mock_wf
        mock_db.execute = AsyncMock(return_value=mock_result)

        service = SupervisorWorkflowService(db=mock_db)
        import asyncio
        asyncio.get_event_loop().run_until_complete(
            service.update_artifacts(
                supervisor_session_id="sv-abc123",
                phase="outline",
                artifacts={"outline": {"title": "星际穿越"}},
            )
        )
        assert mock_wf.current_phase == "outline"
        assert mock_wf.artifacts["outline"] == {"title": "星际穿越"}
```

- [ ] **Step 2: 运行测试，确认失败**

```bash
cd backend && python -m pytest app/tests/unit/core/supervisor/test_workflow_service.py -v
```
Expected: FAIL — module not found

- [ ] **Step 3: 编写实现**

```python
# backend/app/core/supervisor/workflow_service.py
"""
流水线元信息读写服务。

封装 supervisor_workflows 表的 DB 操作：
- 创建流水线记录
- 更新阶段状态
- 追加产物快照
- 追加评估记录
- 查询流水线状态
"""

import json
import logging
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.agent.persist.models import SupervisorWorkflow

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class SupervisorWorkflowService:
    """流水线元信息读写服务。"""

    def __init__(self, db: "AsyncSession"):
        self.db = db

    async def create_workflow(
        self,
        supervisor_session_id: str,
        user_request: str,
    ) -> SupervisorWorkflow:
        """
        创建新的流水线记录。

        在 SupervisorAgent 创建时调用。
        """
        workflow = SupervisorWorkflow(
            supervisor_session_id=supervisor_session_id,
            user_request=user_request,
            current_phase="init",
            artifacts={},
            review_history=[],
            status="running",
        )
        self.db.add(workflow)
        await self.db.commit()
        logger.info(f"[WorkflowService] created workflow sv={supervisor_session_id}")
        return workflow

    async def get_workflow(
        self,
        supervisor_session_id: str,
    ) -> Optional[SupervisorWorkflow]:
        """查询流水线记录。"""
        stmt = select(SupervisorWorkflow).where(
            SupervisorWorkflow.supervisor_session_id == supervisor_session_id
        )
        result = await self.db.execute(stmt)
        return result.scalars().first()

    async def update_phase(
        self,
        supervisor_session_id: str,
        phase: str,
    ) -> None:
        """更新当前阶段。call_sub_agent 完成后调用。"""
        workflow = await self.get_workflow(supervisor_session_id)
        if workflow is None:
            logger.warning(f"[WorkflowService] workflow not found: {supervisor_session_id}")
            return
        workflow.current_phase = phase
        await self.db.commit()
        logger.info(f"[WorkflowService] updated phase sv={supervisor_session_id} -> {phase}")

    async def update_artifacts(
        self,
        supervisor_session_id: str,
        phase: str,
        artifacts: Dict[str, Any],
    ) -> None:
        """
        更新流水线产物。

        call_sub_agent 完成后，将 SubAgent 的 schema_data 追加到 artifacts。
        同时更新 current_phase。
        """
        workflow = await self.get_workflow(supervisor_session_id)
        if workflow is None:
            return

        current = dict(workflow.artifacts or {})
        current[phase] = artifacts
        workflow.artifacts = current
        workflow.current_phase = phase
        await self.db.commit()
        logger.info(
            f"[WorkflowService] updated artifacts sv={supervisor_session_id} "
            f"phase={phase}, artifact_keys={list(current.keys())}"
        )

    async def append_review(
        self,
        supervisor_session_id: str,
        agent_name: str,
        score: float,
        passed: bool,
        feedback: str,
    ) -> None:
        """追加评估记录。call_reviewer 完成后调用。"""
        workflow = await self.get_workflow(supervisor_session_id)
        if workflow is None:
            return

        history = list(workflow.review_history or [])
        history.append({
            "agent": agent_name,
            "score": score,
            "passed": passed,
            "feedback": feedback,
        })
        workflow.review_history = history
        await self.db.commit()
        logger.info(
            f"[WorkflowService] appended review sv={supervisor_session_id} "
            f"agent={agent_name} score={score}"
        )

    async def complete_workflow(
        self,
        supervisor_session_id: str,
        status: str = "completed",
    ) -> None:
        """标记流水线结束（completed / failed）。"""
        workflow = await self.get_workflow(supervisor_session_id)
        if workflow is None:
            return
        workflow.status = status
        await self.db.commit()
        logger.info(f"[WorkflowService] workflow {supervisor_session_id} -> {status}")
```

- [ ] **Step 4: 运行测试，确认通过**

```bash
cd backend && python -m pytest app/tests/unit/core/supervisor/test_workflow_service.py -v
```
Expected: PASS

- [ ] **Step 5: 提交**

```bash
cd backend && git add app/core/supervisor/workflow_service.py app/tests/unit/core/supervisor/test_workflow_service.py && git commit -m "feat(supervisor): add SupervisorWorkflowService for pipeline metadata CRUD"
```
---

## Task 15: `call_sub_agent` 工具集成 DB 持久化

**Files:**
- Modify: `backend/app/core/supervisor/tools.py`（call_sub_agent 写入 DB）
- Modify: `backend/app/core/agent/tool.py`（execute_streaming_tool 支持 db 参数注入）

**目标**：SubAgent 执行完成后，将产物写入 `supervisor_workflows` 表，并将 `supervisor_session_id` 写入 `agent_messages`。

- [ ] **Step 1: 确认 execute_streaming_tool 已有 db 注入逻辑**

查看 Task 4 实现的 `execute_streaming_tool()`，确认其中已有：

```python
kwargs = dict(tool_call.arguments)
if self.db and "db" not in kwargs:
    kwargs["db"] = self.db
```

如果缺少，补上。

- [ ] **Step 2: 修改 call_sub_agent 签名，注入 db 和 workflow_service**

在 `call_sub_agent` 函数中，增加 `workflow_service` 参数（ToolExecutor 通过 kwargs 注入）：

```python
async def call_sub_agent(
    sub_agent_name: str,
    task_description: str,
    context_snapshot: str = "",
    supervisor_context: Optional[SupervisorContext] = None,
    db=None,  # ToolExecutor 注入
    workflow_service=None,  # 新增：WorkflowService 实例
) -> AsyncGenerator[SubAgentEndEvent, None]:
```

- [ ] **Step 3: SubAgent 执行完毕后写入 DB**

在 `call_sub_agent` 的 `yield SubAgentEndEvent` 之前，添加：

```python
    # SubAgent 执行完毕后，写入 DB
    if workflow_service is not None and supervisor_context is not None:
        try:
            await workflow_service.update_artifacts(
                supervisor_session_id=supervisor_context.supervisor_session_id,
                phase=sub_agent_name,
                artifacts=accumulated_result.get("schema_data") or accumulated_result.get("raw_output") or {},
            )
        except Exception as e:
            logger.warning(f"[call_sub_agent] failed to persist artifacts: {e}")
```

- [ ] **Step 4: 修改 SupervisorAgent 构造时注入 workflow_service**

在 `supervisor.py` 的 `__init__` 中，将 `SupervisorWorkflowService` 实例传入 tools 的上下文：

```python
    def __init__(self, ...):
        # ...
        self._tool_ctx = {
            "supervisor_context": self.context,
            "workflow_service": None,  # 由 factory 或 API 层通过此属性注入
        }
```

在 `factory.py` 的 `create_supervisor()` 中，构造 SupervisorAgent 后注入 service：

```python
def create_supervisor(
    user_request: str,
    *,
    db: "AsyncSession" = None,  # 新增参数
    ...
) -> SupervisorAgent:
    supervisor = SupervisorAgent(...)
    if db is not None:
        from app.core.supervisor.workflow_service import SupervisorWorkflowService
        supervisor._tool_ctx["workflow_service"] = SupervisorWorkflowService(db=db)
        # 创建流水线记录
        import asyncio
        asyncio.get_event_loop().run_until_complete(
            supervisor._tool_ctx["workflow_service"].create_workflow(
                supervisor_session_id=supervisor.supervisor_session_id,
                user_request=user_request,
            )
        )
    return supervisor
```

- [ ] **Step 5: 提交**

```bash
cd backend && git add app/core/supervisor/tools.py app/core/supervisor/supervisor.py app/core/supervisor/factory.py && git commit -m "feat(supervisor): persist workflow state to DB in call_sub_agent"
```
---

## 自检清单

- [ ] 所有测试路径存在：`test_context.py`, `test_session.py`, `test_events.py`, `test_tools.py`, `test_reviewer.py`, `test_supervisor.py`, `test_factory.py`, `test_workflow.py`, `test_workflow_service.py`, `test_db_persist.py`
- [ ] Task 1-15 所有步骤完成并提交
- [ ] `call_sub_agent`, `call_reviewer`, `get_workflow_state` 均已注册到 ToolRegistry
- [ ] API 路由 `/supervisor/stream` 可访问
- [ ] `supervisor_workflows` 表已创建（含 artifacts/review_history/status 字段）
- [ ] `agent_messages` 表已加 `supervisor_session_id` 字段
- [ ] SubAgent 完成后产物写入 `supervisor_workflows.artifacts`
- [ ] 每个 Review 结果追加到 `supervisor_workflows.review_history`
- [ ] 无 "TBD"/"TODO" 占位符
- [ ] SupervisorContext 不被 SubAgent 直接访问（隔离原则）
- [ ] SubAgent 工具支持 async generator 流式事件透传
- [ ] 多用户并发无数据串扰（每个 Supervisor 独立 session_id）
