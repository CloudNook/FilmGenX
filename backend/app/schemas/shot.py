"""
单镜头（Shot）的请求/响应 Schema。
"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, model_validator

from app.schemas.base import BaseResponse


class CameraConfig(BaseModel):
    """摄像机参数。"""
    shot_type: Optional[str] = Field(None, description="景别：ECU/CU/MCU/MS/MLS/LS/ELS")
    angle: Optional[str] = Field(None, description="角度：eye_level/high_angle/low_angle/dutch")
    movement: Optional[str] = Field(None, description="运动：static/pan/tilt/dolly/crane/handheld")
    focal_length: Optional[str] = Field(None, description="焦距描述，如 '35mm 广角'")
    depth_of_field: Optional[str] = Field(None, description="景深描述，如 '浅景深，背景虚化'")


class CompositionConfig(BaseModel):
    """构图描述。"""
    subject_position: Optional[str] = Field(None, description="主体位置，如 '三分线左侧'")
    foreground: Optional[str] = Field(None, description="前景元素描述")
    midground: Optional[str] = Field(None, description="中景元素描述")
    background: Optional[str] = Field(None, description="背景元素描述")
    leading_lines: Optional[str] = Field(None, description="引导线描述")


class CharacterInShot(BaseModel):
    """镜头中的单个角色配置。"""
    char_version_id: int = Field(..., description="角色版本ID")
    action: Optional[str] = Field(None, description="动作描述")
    expression: Optional[str] = Field(None, description="表情描述")
    emotion_intensity: Optional[int] = Field(None, ge=1, le=10, description="情绪强度 1-10")
    sfx: Optional[Dict[str, Any]] = Field(None, description="角色特效：斗气颜色/强度/粒子效果")


class EnvironmentConfig(BaseModel):
    """环境配置。"""
    location_id: Optional[int] = Field(None, description="场景地点ID")
    location_version_id: Optional[int] = Field(None, description="场景变体ID")
    time_of_day: Optional[str] = Field(None, description="时间：dawn/day/dusk/night")
    weather: Optional[str] = Field(None, description="天气：clear/cloudy/rain/snow/fog/storm")
    lighting: Optional[str] = Field(None, description="光照描述")
    atmosphere: Optional[str] = Field(None, description="氛围描述")


class ShotCreate(BaseModel):
    """创建单镜头请求体。"""
    shot_code: str = Field(..., max_length=30, description="业务ID，如 DQCK_001_S003")
    sequence: int = Field(..., ge=1, description="在分镜脚本中的顺序")
    duration_sec: float = Field(3.0, gt=0, le=30, description="时长（秒）")

    # 摄像机与构图
    camera: Optional[CameraConfig] = None
    composition: Optional[CompositionConfig] = None

    # 角色（支持多角色）
    characters_config: Optional[List[CharacterInShot]] = Field(None, description="多角色详细配置")

    # 环境
    environment: Optional[EnvironmentConfig] = Field(None, description="环境配置")

    # 台词
    dialogue_character: Optional[str] = Field(None, max_length=50)
    dialogue_text: Optional[str] = None
    dialogue_delivery: Optional[Dict[str, Any]] = Field(None, description="台词情感参数")

    # 音频
    sound_design: Optional[Dict[str, Any]] = Field(None, description="音效设计")

    # 转场
    transition_in: Optional[str] = Field(None, max_length=50)
    transition_out: Optional[str] = Field(None, max_length=50)
    transition_notes: Optional[str] = None

    # 依赖
    dependencies: List[Dict[str, Any]] = Field(default_factory=list)

    # 生成提示词
    image_prompt: Optional[str] = None
    negative_prompt: Optional[str] = None
    style_preset: Optional[str] = Field(None, max_length=100)

    reference_images: Optional[List[Dict[str, Any]]] = Field(
        None,
        description="用户选择的参考图列表",
    )
    generated_images: Optional[List[Dict[str, Any]]] = Field(
        None,
        description="AI生成的图片列表",
    )


class ShotUpdate(BaseModel):
    """更新单镜头请求体（所有字段可选）。"""
    sequence: Optional[int] = Field(None, ge=1)
    duration_sec: Optional[float] = Field(None, gt=0, le=30)
    camera: Optional[CameraConfig] = None
    composition: Optional[CompositionConfig] = None
    characters_config: Optional[List[CharacterInShot]] = None
    environment: Optional[EnvironmentConfig] = None
    dialogue_character: Optional[str] = Field(None, max_length=50)
    dialogue_text: Optional[str] = None
    dialogue_delivery: Optional[Dict[str, Any]] = None
    sound_design: Optional[Dict[str, Any]] = None
    transition_in: Optional[str] = Field(None, max_length=50)
    transition_out: Optional[str] = Field(None, max_length=50)
    transition_notes: Optional[str] = None
    dependencies: Optional[List[Dict[str, Any]]] = None
    image_prompt: Optional[str] = None
    negative_prompt: Optional[str] = None
    style_preset: Optional[str] = Field(None, max_length=100)
    # QC 字段
    qc_character_consistency: Optional[bool] = None
    qc_lighting_match: Optional[bool] = None
    qc_action_continuity: Optional[bool] = None
    qc_approved: Optional[bool] = None
    qc_score: Optional[int] = Field(None, ge=0, le=100)
    status: Optional[str] = Field(
        None,
        pattern="^(draft|generating|review|approved|rejected)$",
        description="状态：draft / generating / review / approved / rejected",
    )
    reference_images: Optional[List[Dict[str, Any]]] = Field(
        None,
        description="用户选择的参考图列表",
    )
    generated_images: Optional[List[Dict[str, Any]]] = Field(
        None,
        description="AI生成的图片列表",
    )


class ShotResponse(BaseResponse):
    """单镜头详情响应。"""
    storyboard_id: int
    shot_group_id: Optional[int] = None
    shot_code: str
    sequence: int
    duration_sec: float
    camera: Optional[dict]
    composition: Optional[dict]
    characters_config: Optional[list]
    environment: Optional[dict]
    dialogue_character: Optional[str]
    dialogue_text: Optional[str]
    dialogue_delivery: Optional[dict]
    sound_design: Optional[dict]
    transition_in: Optional[str]
    transition_out: Optional[str]
    transition_notes: Optional[str]
    dependencies: list
    image_prompt: Optional[str]
    negative_prompt: Optional[str]
    style_preset: Optional[str]
    qc_character_consistency: bool
    qc_lighting_match: bool
    qc_action_continuity: bool
    qc_approved: bool
    qc_score: Optional[int]
    status: str
    video_url: Optional[str] = None
    reference_images: list = Field(default_factory=list, description="用户选择的参考图")
    generated_images: list = Field(default_factory=list, description="AI生成的图片")

    @model_validator(mode="before")
    @classmethod
    def _normalize_characters_config(cls, data):
        """Normalize characters_config:
        - wrap single dicts in a list (legacy DB entries)
        - coerce strings to null (AI may return a description string for non-character shots)
        """
        if hasattr(data, "__dict__"):
            data = {k: v for k, v in data.__dict__.items() if not k.startswith("_")}
        if isinstance(data, dict):
            cc = data.get("characters_config")
            if isinstance(cc, str):
                # AI returned a description string instead of a list — treat as null
                data["characters_config"] = None
            elif cc is not None and isinstance(cc, dict):
                data["characters_config"] = [cc]
        return data
