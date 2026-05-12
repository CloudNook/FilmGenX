"""
Sub-agent 结构化输出 schema（业务层契约）。

每一个 sub-agent 的产出形态由这里定义的 Pydantic 类决定，schema 通过
``Class.model_json_schema()`` 转出 JSON Schema 喂给 LLM 的 response_schema。

设计要点：
- 业务层（schemas/）暴露的 Pydantic 类，core 框架不感知。
- 后期 spec 演化只动这些类，不动框架。
- 每个 schema 配套提供 ``json_schema()`` 便捷方法返回 LLM 可消费的 JSON Schema。

链路对齐 ``backend/app/core/supervisor/registry.py`` 的 workflow 定义：

  outline → script → storyboard → visual_style → character_ref → scene_ref → video_prompt
"""

# Layer 1：创作层
from app.schemas.agent_outputs.outline import OutlineOutput
from app.schemas.agent_outputs.script import ScriptOutput
from app.schemas.agent_outputs.storyboard import StoryboardOutput

# Layer 2：视觉锚点
from app.schemas.agent_outputs.visual_style import VisualStyleGuide

# Layer 3：参考图设计
from app.schemas.agent_outputs.character_ref import CharacterRefSet
from app.schemas.agent_outputs.scene_ref import SceneRefSet

# Layer 4：视频提示词（直接消费 storyboard + character_ref / scene_ref 参考图）
from app.schemas.agent_outputs.video_prompt import VideoPromptSet

__all__ = [
    "OutlineOutput",
    "ScriptOutput",
    "StoryboardOutput",
    "VisualStyleGuide",
    "CharacterRefSet",
    "SceneRefSet",
    "VideoPromptSet",
]
