"""
单镜头（Shot）的请求/响应 Schema。
"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

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


class ShotCreate(BaseModel):
    """创建单镜头请求体。"""
    shot_code: str = Field(..., max_length=30, description="业务ID，如 DQCK_001_S003")
    sequence: int = Field(..., ge=1, description="在分镜脚本中的顺序")
    duration_sec: float = Field(3.0, gt=0, le=30, description="时长（秒）")

    # 摄像机与构图
    camera: Optional[CameraConfig] = None
    composition: Optional[CompositionConfig] = None

    # 角色
    character_id: Optional[int] = None
    char_version_id: Optional[int] = None
    character_action: Optional[str] = None
    character_expression: Optional[str] = None
    character_emotion_intensity: Optional[int] = Field(None, ge=1, le=10)
    character_sfx: Optional[Dict[str, Any]] = Field(None, description="角色特效：斗气颜色/强度/粒子效果")

    # 环境
    location_id: Optional[int] = Field(None, description="场景地点ID")
    location_version_id: Optional[int] = Field(None, description="场景变体ID（使用非默认版本时填写）")
    environment: Optional[Dict[str, Any]] = Field(None, description="环境配置：时间/天气/光照/氛围")

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


class ShotUpdate(BaseModel):
    """更新单镜头请求体（所有字段可选）。"""
    sequence: Optional[int] = Field(None, ge=1)
    duration_sec: Optional[float] = Field(None, gt=0, le=30)
    camera: Optional[CameraConfig] = None
    composition: Optional[CompositionConfig] = None
    character_id: Optional[int] = None
    char_version_id: Optional[int] = None
    character_action: Optional[str] = None
    character_expression: Optional[str] = None
    character_emotion_intensity: Optional[int] = Field(None, ge=1, le=10)
    character_sfx: Optional[Dict[str, Any]] = None
    location_id: Optional[int] = Field(None, description="场景地点ID")
    location_version_id: Optional[int] = Field(None, description="场景变体ID（使用非默认版本时填写）")
    environment: Optional[Dict[str, Any]] = None
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


class ShotResponse(BaseResponse):
    """单镜头详情响应。"""
    storyboard_id: int
    shot_code: str
    sequence: int
    duration_sec: float
    camera: Optional[dict]
    composition: Optional[dict]
    character_id: Optional[int]
    char_version_id: Optional[int]
    character_action: Optional[str]
    character_expression: Optional[str]
    character_emotion_intensity: Optional[int]
    character_sfx: Optional[dict]
    location_id: Optional[int]
    location_version_id: Optional[int]
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
