"""
Agent 工厂函数。

返回 Agent 实例，具体执行需显式调用 agent.run() / agent.stream()。

支持从数据库加载 Skill 摘要，注入到 system prompt。
"""

import json
import logging
from typing import Any, Dict, List, Literal, Optional, Union

from app.core.agent.agent import Agent
from app.core.agent.base import AgentConfig
from app.core.agent.persist.base import PersistStrategy
from app.core.agent.persist.redis_strategy import RedisPersistStrategy
from app.core.middleware.chain import AgentMiddleware

logger = logging.getLogger(__name__)

# "redis" 是框架内置快捷方式；DB 持久化需调用方自行构造 DBPersistStrategy 实例传入
PersistArg = Union[Literal["redis"], PersistStrategy, None]

# Skill 注入系统提示词的默认前缀模板
DEFAULT_SKILL_INJECT_TEMPLATE = """

## 专业知识 (Skills)

当你需要专业领域知识时，调用 load_skill 工具加载对应 Skill。
以下是当前会话可用的 Skills：

{skill_lite_json}

## Skill 使用规则

- 在开始涉及剧本、灯光、运镜、调色等专业领域的任务前，先调用 load_skill 获取对应知识
- 调用示例：load_skill(skill_name="screenwriting", fields=["content", "constraints"])
- 如需了解 Skill 的完整参数，可调用 load_skill(skill_name="xxx", fields=["parameters"])
"""


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
    skill_lite_list: List[Dict[str, Any]],
) -> str:
    """将 Skill 摘要注入到系统提示词中。"""
    if not skill_lite_list:
        return base_prompt

    skill_json = json.dumps(skill_lite_list, ensure_ascii=False, indent=2)
    skill_section = DEFAULT_SKILL_INJECT_TEMPLATE.format(skill_lite_json=skill_json)
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
    skills: Optional[List[str]] = None,
    skill_lite_list: Optional[List[Dict[str, Any]]] = None,
    max_loop: int = 20,
    persist: PersistArg = None,
    middlewares: Optional[List[AgentMiddleware]] = None,
) -> Agent:
    """
    创建 Agent 实例。

    注意：此方法仅创建实例，不执行。
    实际执行需调用 agent.run() 或 agent.stream()。

    Args:
        agent_name:      Agent 名称
        session_id:      会话 ID，用于多轮对话持久化
        prompt:          系统提示词（基础部分）
        model:           LLM 模型名称
        temperature:     温度参数
        max_tokens:      最大 token 数
        tools:           工具列表
        skills:          Skill 名称列表（仅记录到 config，技能注入由 skill_lite_list 控制）
        skill_lite_list: Skill 摘要列表（从 DB 加载，会注入到 system prompt）
        max_loop:        最大循环次数
        persist:         持久化策略，"redis" | PersistStrategy 实例 | None
                          DB 持久化示例：persist=DBPersistStrategy(db=session)
        middlewares:     中间件列表

    Returns:
        Agent 实例，需调用 run() / stream() 执行
    """
    # 注入 Skill 摘要到 system prompt
    full_prompt = _build_system_prompt_with_skills(prompt, skill_lite_list or [])

    config = AgentConfig(
        agent_name=agent_name,
        prompt=full_prompt,
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
        tools=tools or [],
        skill_names=skills or [],
        max_loop=max_loop,
    )

    persist_strategy = _resolve_persist(persist)

    if skill_lite_list:
        logger.info(
            f"[create_agent] agent={agent_name}, "
            f"skills_injected={len(skill_lite_list)}, "
            f"persist={persist_strategy.name if persist_strategy else 'none'}"
        )

    return Agent(
        config=config,
        session_id=session_id,
        persist=persist_strategy,
        middlewares=middlewares,
    )
