"""
Phase 1 扩展链路装配回归（路径 B）。

钉死：
- workflow 含 7 个节点 + 正确依赖链
- registry 含 7 个 sub-agent，4 个新 agent prompt / response_schema / reviewer 装载到位
- character_ref / scene_ref / video_prompt 在 default skill 工具之外额外挂载 media tools
- 其他 4 个 agent 不挂 media tools
"""

from __future__ import annotations

import pytest

from app.agents import (
    REVIEWER_PROMPT,
    SUB_AGENT_PROMPT,
    SUB_AGENT_RESPONSE_SCHEMA,
)
from app.core.supervisor.registry import (
    build_default_registry,
    build_default_workflow_definitions,
)


EXPECTED_NODES = [
    "outline",
    "script",
    "storyboard",
    "visual_style",
    "character_ref",
    "scene_ref",
    "video_prompt",
]

EXPECTED_DEPENDENCIES = {
    "outline": [],
    "script": ["outline"],
    "storyboard": ["script"],
    "visual_style": ["storyboard"],
    "character_ref": ["visual_style"],
    "scene_ref": ["character_ref"],
    "video_prompt": ["scene_ref"],
}

# 全部 7 个 sub-agent 都允许调工具（load_skill + 可选 media gen），所以全部**不挂
# response_schema**——Gemini 的 structured output 与 function calling 互斥，挂了
# 工具通道关掉。JSON 输出靠 <output>...</output> 包裹 + supervisor 端 Pydantic 校验。
SCHEMA_FREE_AGENTS = [
    "outline_agent",
    "script_agent",
    "storyboard_agent",
    "visual_style_agent",
    "character_ref_agent",
    "scene_ref_agent",
    "video_prompt_agent",
]

# 出图 / 出视频权限只发给 3 个资产产出 agent。
MEDIA_PRODUCING_ASSET_AGENTS = [
    "character_ref_agent",
    "scene_ref_agent",
    "video_prompt_agent",
]

NEW_AGENTS = [
    "visual_style_agent",
    *MEDIA_PRODUCING_ASSET_AGENTS,
]

ALL_AGENTS = [
    "outline_agent",
    "script_agent",
    "storyboard_agent",
    *NEW_AGENTS,
]


def test_workflow_definitions_contain_seven_nodes_in_order():
    nodes = build_default_workflow_definitions()
    assert [n.key for n in nodes] == EXPECTED_NODES


def test_workflow_definitions_match_expected_dependencies():
    nodes = {n.key: n for n in build_default_workflow_definitions()}
    for key, deps in EXPECTED_DEPENDENCIES.items():
        assert nodes[key].depends_on == deps, f"{key} 依赖错位"


def test_default_registry_contains_seven_agents():
    registry = build_default_registry()
    assert registry.agent_names() == ALL_AGENTS


@pytest.mark.parametrize("name", NEW_AGENTS)
def test_new_agent_has_domain_prompt_and_reviewer(name: str):
    registry = build_default_registry()
    agent = registry.get(name)
    assert agent is not None

    assert agent.prompt == SUB_AGENT_PROMPT[name]
    assert len(agent.prompt) > 200, f"{name} prompt 太短，可能退化成占位"

    assert agent.reviewer is not None
    assert agent.reviewer.agent.config.prompt == REVIEWER_PROMPT[name]
    assert agent.reviewer.min_score == 7.5
    assert agent.reviewer.max_revision_rounds == 2
    assert agent.reviewer.on_exhausted == "accept_last"


@pytest.mark.parametrize("name", SCHEMA_FREE_AGENTS)
def test_all_sub_agents_have_no_response_schema(name: str):
    """所有 sub-agent 都需要调工具（至少 load_skill），所以全部不挂 response_schema。

    Gemini structured output 与 function calling 互斥；JSON 输出靠
    <output>...</output> 包裹 + supervisor 端 Pydantic 校验。
    """
    registry = build_default_registry()
    agent = registry.get(name)
    assert agent.response_schema is None
    assert SUB_AGENT_RESPONSE_SCHEMA[name] is None


def _tool_names(agent) -> list[str]:
    return [t.get("name") for t in agent.tools]


@pytest.mark.parametrize(
    "name",
    [
        "character_ref_agent",
        "scene_ref_agent",
    ],
)
def test_image_producing_agents_have_generate_image(name: str):
    """character / scene 两个出图角色都需要 generate_image，用于
    出三视图 / 场景参考图。"""
    agent = build_default_registry().get(name)
    names = _tool_names(agent)
    assert "load_skill" in names
    assert "load_skill_reference" in names
    assert "generate_image" in names
    # 不应混进视频工具或老的拆分工具
    assert "generate_video" not in names
    assert "generate_image_pro" not in names
    assert "generate_image_flash" not in names


def test_video_prompt_agent_has_video_tool():
    agent = build_default_registry().get("video_prompt_agent")
    names = _tool_names(agent)
    assert "load_skill" in names
    assert "load_skill_reference" in names
    assert "generate_video" in names
    # concat_videos：按 storyboard 顺序拼接多段视频出成片
    assert "concat_videos" in names
    assert "generate_image" not in names
    assert "generate_video_text_to_video" not in names
    assert "generate_video_image_to_video" not in names


@pytest.mark.parametrize(
    "name",
    [
        "outline_agent",
        "script_agent",
        "storyboard_agent",
        "visual_style_agent",
    ],
)
def test_non_asset_agents_only_have_default_skill_tools(name: str):
    """outline / script / storyboard / visual_style 不产出图像 / 视频资产，
    不应挂 media 工具。"""
    agent = build_default_registry().get(name)
    names = _tool_names(agent)
    assert names == ["load_skill", "load_skill_reference"], (
        f"{name} 不应挂载 media 工具，但挂了 {names}"
    )


def test_node_keys_align_with_workflow_nodes():
    nodes = {n.key for n in build_default_workflow_definitions()}
    for agent in build_default_registry().agents:
        for key in agent.node_keys:
            assert key in nodes, f"{agent.name} 引用的 node {key} 不在 workflow 里"
