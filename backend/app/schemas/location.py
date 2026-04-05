"""
场景地点（Location）的请求/响应 Schema。
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from app.schemas.base import BaseResponse


# ========== Atmosphere Config ==========

class AtmosphereConfig(BaseModel):
    """氛围配置。"""
    weather: Optional[str] = Field(None, description="天气：clear / cloudy / rain / snow / fog / storm")
    lighting: Optional[str] = Field(None, description="光照描述")
    mood: Optional[str] = Field(None, description="氛围情绪")
    color_tone: Optional[str] = Field(None, description="色调倾向")


# ========== Location Schemas ==========

class LocationCreate(BaseModel):
    """创建场景请求体。"""
    name: str = Field(..., max_length=100, description="场景名称")
    aliases: List[str] = Field(default_factory=list, description="别名列表")
    location_type: str = Field(
        "outdoor",
        pattern="^(indoor|outdoor|fantasy|mixed)$",
        description="场景类型"
    )
    domain: Optional[str] = Field(None, max_length=50, description="所属势力/领域")
    description: Optional[str] = Field(None, description="场景详细描述")
    architectural_style: Optional[str] = Field(None, max_length=100, description="建筑风格")
    key_elements: List[str] = Field(default_factory=list, description="标志性元素")
    default_atmosphere: Optional[AtmosphereConfig] = Field(None, description="默认氛围配置")
    time_variants: Optional[Dict[str, str]] = Field(
        None,
        description="时间变体描述：{dawn, day, dusk, night}"
    )
    base_background_prompt: Optional[str] = Field(None, description="背景生成基础提示词（英文）")
    negative_prompt: Optional[str] = Field(None, description="负面提示词")
    style_preset: Optional[str] = Field(None, max_length=100, description="风格预设")
    reference_image_urls: List[str] = Field(default_factory=list, description="参考图URL列表")
    tags: List[str] = Field(default_factory=list, description="标签列表")


class LocationUpdate(BaseModel):
    """更新场景请求体。"""
    name: Optional[str] = Field(None, max_length=100)
    aliases: Optional[List[str]] = None
    location_type: Optional[str] = Field(None, pattern="^(indoor|outdoor|fantasy|mixed)$")
    domain: Optional[str] = Field(None, max_length=50)
    description: Optional[str] = None
    architectural_style: Optional[str] = Field(None, max_length=100)
    key_elements: Optional[List[str]] = None
    default_atmosphere: Optional[AtmosphereConfig] = None
    time_variants: Optional[Dict[str, str]] = None
    base_background_prompt: Optional[str] = None
    negative_prompt: Optional[str] = None
    style_preset: Optional[str] = Field(None, max_length=100)
    reference_image_urls: Optional[List[str]] = None
    tags: Optional[List[str]] = None
    is_active: Optional[bool] = None


class LocationResponse(BaseResponse):
    """场景详情响应。"""
    project_id: int
    loc_code: str
    name: str
    aliases: list
    location_type: str
    domain: Optional[str]
    description: Optional[str]
    architectural_style: Optional[str]
    key_elements: list
    default_atmosphere: Optional[dict]
    time_variants: Optional[dict]
    base_background_prompt: Optional[str]
    negative_prompt: Optional[str]
    style_preset: Optional[str]
    reference_image_urls: list
    tags: list
    is_active: bool
    usage_count: int
    # 关联


class LocationBrief(BaseModel):
    """场景简略信息（用于下拉选择、列表展示）。"""
    model_config = {"from_attributes": True}

    id: int
    loc_code: str
    name: str
    location_type: str
    domain: Optional[str]
    is_active: bool


# ========== LocationVersion Schemas ==========

class LocationVersionCreate(BaseModel):
    """创建场景变体请求体。"""
    version_code: str = Field(
        ...,
        max_length=30,
        pattern=r"^[a-z0-9_]+$",
        description="版本标识，如 'night' / 'battle_damaged'"
    )
    label: str = Field(..., max_length=100, description="版本显示名称")
    description: Optional[str] = Field(None, description="该变体的特殊描述")
    atmosphere_override: Optional[AtmosphereConfig] = Field(None, description="覆盖主场景的氛围配置")
    time_of_day: Optional[str] = Field(
        None,
        pattern="^(dawn|day|dusk|night)$",
        description="时间"
    )
    weather: Optional[str] = Field(
        None,
        pattern="^(clear|cloudy|rain|snow|fog|storm)$",
        description="天气"
    )
    additional_elements: List[str] = Field(
        default_factory=list,
        description="额外元素，如 ['战火痕迹', '破碎的石柱']"
    )
    removed_elements: List[str] = Field(
        default_factory=list,
        description="移除的元素，如 ['石碑']（被摧毁）"
    )
    prompt_suffix: Optional[str] = Field(None, description="追加到基础提示词后的内容")
    full_prompt: Optional[str] = Field(None, description="完整提示词（直接覆盖）")
    reference_image_urls: List[str] = Field(default_factory=list, description="该变体专属参考图")
    applicable_scene_codes: List[str] = Field(
        default_factory=list,
        description="适用的片段code列表"
    )
    is_default: bool = Field(False, description="是否为默认版本")


class LocationVersionUpdate(BaseModel):
    """更新场景变体请求体。"""
    label: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = None
    atmosphere_override: Optional[AtmosphereConfig] = None
    time_of_day: Optional[str] = Field(None, pattern="^(dawn|day|dusk|night)$")
    weather: Optional[str] = Field(None, pattern="^(clear|cloudy|rain|snow|fog|storm)$")
    additional_elements: Optional[List[str]] = None
    removed_elements: Optional[List[str]] = None
    prompt_suffix: Optional[str] = None
    full_prompt: Optional[str] = None
    reference_image_urls: Optional[List[str]] = None
    applicable_scene_codes: Optional[List[str]] = None
    is_default: Optional[bool] = None


class LocationVersionResponse(BaseResponse):
    """场景变体详情响应。"""
    location_id: int
    version_code: str
    label: str
    description: Optional[str]
    atmosphere_override: Optional[dict]
    time_of_day: Optional[str]
    weather: Optional[str]
    additional_elements: list
    removed_elements: list
    prompt_suffix: Optional[str]
    full_prompt: Optional[str]
    reference_image_urls: list
    applicable_scene_codes: list
    is_default: bool


class LocationVersionBrief(BaseModel):
    """场景变体简略信息。"""
    model_config = {"from_attributes": True}

    id: int
    version_code: str
    label: str
    time_of_day: Optional[str]
    weather: Optional[str]
    is_default: bool


# ========== 组合响应 ==========

class LocationWithVersionsResponse(LocationResponse):
    """场景详情（含所有变体）。"""
    versions: List[LocationVersionResponse] = Field(default_factory=list)


class LocationDetailResponse(LocationResponse):
    """场景完整详情（含默认变体信息）。"""
    versions: List[LocationVersionResponse] = Field(default_factory=list)
    default_version: Optional[LocationVersionBrief] = None
    version_count: int = 0


# 更新 forward references
LocationResponse.model_rebuild()
LocationWithVersionsResponse.model_rebuild()
LocationDetailResponse.model_rebuild()
