"""
Agent 工厂函数。

返回 Agent 实例，具体执行需显式调用 agent.run() / agent.stream()。

支持从数据库加载 Skill 摘要，注入到 system prompt。
"""

import json
import logging
from typing import Any, Dict, List, Literal, Optional, Union

from app.core.agent.agent import Agent
from app.core.agent.base import AgentConfig, Reviewer
from app.core.agent.memory.config import MemoryConfig
from app.core.agent.memory.harness import MemoryHarness
from app.core.agent.memory.tool import build_memory_save_tool_schema
from app.core.agent.persist.base import PersistStrategy
from app.core.agent.persist.redis_strategy import RedisPersistStrategy
from app.core.middleware.chain import AgentMiddleware

logger = logging.getLogger(__name__)

# "redis" 是框架内置快捷方式；DB 持久化需调用方自行构造 DBPersistStrategy 实例传入
PersistArg = Union[Literal["redis"], PersistStrategy, None]

# Skill 注入系统提示词的默认前缀模板
# Claude SKILL.md 风格三层渐进披露：
# - L1（本段）：只放 name / description / target_agents / tags，永远在 context
# - L2：``load_skill(skill_name)`` 拉 body
# - L3：``load_skill_reference(skill_name, ref_key)`` 拉 reference 子文档
DEFAULT_SKILL_INJECT_TEMPLATE = """

## 可用 Skills（L1 元信息）

下列是当前可用的领域 Skill 摘要。description 通常以 "Use when ... to ..." 句式写出激活条件，请据此判断是否进入下一层。

{skill_meta_json}

## Skill 渐进式披露规则

1. 默认你只看得到上面的 L1 元信息。判断当前任务确实需要某个 Skill 时，再加载它。
2. 加载 Skill 主体（L2）：调用 ``load_skill(skill_name="<name>")``，返回 body markdown。
3. body 内可能出现以下 @ 引用标记，对应不同的工具调用：
   - ``@ref:<key>``           → 当前 skill 的某个 reference；调用 ``load_skill_reference(skill_name="<current>", ref_key="<key>")``
   - ``@skill:<name>``        → 跨 skill 整体；判断需要时调用 ``load_skill(skill_name="<name>")``
   - ``@skill:<name>#<key>``  → 跨 skill 子节；判断需要时调用 ``load_skill_reference(skill_name="<name>", ref_key="<key>")``
4. 不要预先把所有引用都加载完——按需加载，避免上下文膨胀。

注意：上面的 Skills 列表只展示与你这个 agent 强相关的 skill；任何 ``@skill:`` 跨域引用你都可以照常 load，框架不会拦截。"""


def _resolve_persist(persist: PersistArg) -> Optional[PersistStrategy]:
    if persist is None:
        return None
    if isinstance(persist, PersistStrategy):
        return persist
    if persist == "redis":
        return RedisPersistStrategy()
    raise ValueError(f"未知的 persist 参数：{persist!r}，可选值：'redis' | PersistStrategy 实例 | None")


def _build_system_prompt_with_skills(
    base_prompt: str,
    skill_meta_list: List[Dict[str, Any]],
) -> str:
    """将 L1 skill 元信息注入到系统提示词中。

    ``skill_meta_list`` 每项形如 ``{name, description, target_agents, tags}``，
    与 ``SkillService.list_active_meta()`` 的返回一致。
    """
    if not skill_meta_list:
        return base_prompt

    skill_json = json.dumps(skill_meta_list, ensure_ascii=False, indent=2)
    skill_section = DEFAULT_SKILL_INJECT_TEMPLATE.format(skill_meta_json=skill_json)
    return (base_prompt or "").rstrip() + skill_section


def create_agent(
    agent_name: str,
    session_id: str,
    prompt: str = "",
    *,
    model: str = "gemini-3-flash-preview",
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None,
    tools: Optional[List[Dict[str, Any]]] = None,
    skill_names: Optional[List[str]] = None,
    max_loop: int = 20,
    persist: PersistArg = None,
    middlewares: Optional[List[AgentMiddleware]] = None,
    reviewer: Optional[Reviewer] = None,
    response_schema: Optional[Dict[str, Any]] = None,
    memory: Optional[MemoryConfig] = None,
) -> Agent:
    """
    创建 Agent 实例。

    注意：此方法仅创建实例，不执行。
    实际执行需调用 agent.run() 或 agent.stream()。

    Skill 加载时机：run() / stream() 开始时根据 skill_names 懒加载，
    DB session 从 persist（DBPersistStrategy）中获取。

    Args:
        agent_name:      Agent 名称
        session_id:      会话 ID，用于多轮对话持久化
        prompt:          系统提示词（基础部分）
        model:           LLM 模型名称
        temperature:     温度参数
        max_tokens:      最大 token 数
        tools:           工具列表
        skill_names:     绑定的 Skill 名称列表，run/stream 时懒加载注入 prompt
        max_loop:        最大循环次数
        persist:         持久化策略，"redis" | PersistStrategy 实例 | None
        middlewares:     中间件列表
        reviewer:        可选 Reviewer（满足 Reviewer Protocol，例如 ReviewerAgent 实例）。
                         不传则完全无 review 链路；传入则候选输出会经过 reviewer 评审。
        response_schema: 可选 JSON Schema，启用 Provider 原生结构化输出。

    Returns:
        Agent 实例，需调用 run() / stream() 执行
    """
    resolved_tools = list(tools or [])

    # Memory 挂载：如果声明了 memory 配置，构造 harness 并按需把 memory_save
    # 工具 schema 注入 tools 表（运行期 ToolExecutor 已经能拿到 harness 实例，
    # 通过 Agent 内部 extra_kwargs 注入 memory_handler）。
    memory_harness: Optional[MemoryHarness] = None
    if memory is not None:
        memory_harness = MemoryHarness(
            memory,
            agent_name=agent_name,
            session_id=session_id,
        )
        if memory.save_tool_enabled:
            existing_names = {t.get("name") for t in resolved_tools}
            if "memory_save" not in existing_names:
                resolved_tools.append(build_memory_save_tool_schema())

    config = AgentConfig(
        agent_name=agent_name,
        prompt=prompt,
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
        tools=resolved_tools,
        max_loop=max_loop,
        response_schema=response_schema,
    )

    persist_strategy = _resolve_persist(persist)

    return Agent(
        config=config,
        session_id=session_id,
        skill_names=skill_names or [],
        persist=persist_strategy,
        middlewares=middlewares,
        reviewer=reviewer,
        memory=memory_harness,
    )
