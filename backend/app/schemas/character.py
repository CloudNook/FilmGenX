"""
角色（Character / CharacterVersion）的请求/响应 Schema。
"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from app.schemas.base import BaseResponse


# ---------------------------------------------------------------------------
# 角色图片生成相关
# ---------------------------------------------------------------------------

class CharacterViewGenerateRequest(BaseModel):
    """生成角色三视图请求体。"""
    view_type: str = Field(..., description="视图类型：front / side / back")
    prompt_override: Optional[str] = Field(None, description="覆盖默认提示词")


class CharacterStateImageGenerateRequest(BaseModel):
    """生成角色状态图片请求体。"""
    state_type: str = Field(..., description="状态类型：anger / happy / sad / skill_release / battle / etc")
    state_description: Optional[str] = Field(None, description="状态详细描述")
    prompt_override: Optional[str] = Field(None, description="覆盖默认提示词")


class CharacterImageUploadRequest(BaseModel):
    """角色图片上传请求体。"""
    image_type: str = Field(..., description="图片类型：reference / view_front / view_side / view_back / state")
    state_key: Optional[str] = Field(None, description="状态图片的键名（当 image_type=state 时必填）")


class CharacterImageUploadResponse(BaseModel):
    """角色图片上传响应。"""
    upload_url: str = Field(..., description="上传目标 URL")
    file_key: str = Field(..., description="文件在 OSS 中的 key")
    image_url: str = Field(..., description="上传完成后的访问 URL")


# ---------------------------------------------------------------------------
# CharacterVersion
# ---------------------------------------------------------------------------

class CharacterVersionCreate(BaseModel):
    """创建角色版本请求体。"""
    version_code: str = Field(..., max_length=30, description="版本标识，如 v1_teen")
    label: str = Field(..., max_length=100, description="显示名称，如 '少年期（15-16岁）'")
    applicable_chapter_start: Optional[str] = Field(None, max_length=50)
    applicable_chapter_end: Optional[str] = Field(None, max_length=50)
    age_description: Optional[str] = Field(None, max_length=50)
    height_cm: Optional[int] = Field(None, gt=0, le=300)
    build_description: Optional[str] = None
    face_description: Optional[str] = None
    hair_description: Optional[str] = None
    costumes: Optional[Dict[str, Any]] = Field(None, description="服装配置字典，如 {default: '白袍', battle: '战袍'}")
    dou_qi_color: Optional[str] = Field(None, max_length=10, description="斗气颜色HEX，如 #FFB830")
    dou_qi_level: Optional[str] = Field(None, max_length=20, description="境界，如 斗皇")
    key_features: List[str] = Field(default_factory=list, description="标志性细节列表")
    reference_image_urls: List[str] = Field(default_factory=list, description="参考图URL列表")
    base_image_prompt: Optional[str] = Field(None, description="该版本的基础图像提示词（英文）")


class CharacterVersionUpdate(BaseModel):
    """更新角色版本请求体。"""
    label: Optional[str] = Field(None, max_length=100)
    applicable_chapter_start: Optional[str] = Field(None, max_length=50)
    applicable_chapter_end: Optional[str] = Field(None, max_length=50)
    age_description: Optional[str] = Field(None, max_length=50)
    height_cm: Optional[int] = Field(None, gt=0, le=300)
    build_description: Optional[str] = None
    face_description: Optional[str] = None
    hair_description: Optional[str] = None
    costumes: Optional[Dict[str, Any]] = None
    dou_qi_color: Optional[str] = Field(None, max_length=10)
    dou_qi_level: Optional[str] = Field(None, max_length=20)
    key_features: Optional[List[str]] = None
    reference_image_urls: Optional[List[str]] = None
    base_image_prompt: Optional[str] = None
    # 三视图
    view_front_url: Optional[str] = None
    view_side_url: Optional[str] = None
    view_back_url: Optional[str] = None
    # 状态图片
    state_images: Optional[Dict[str, str]] = None


class CharacterVersionResponse(BaseResponse):
    """角色版本详情响应。"""
    character_id: int
    version_code: str
    label: str
    applicable_chapter_start: Optional[str]
    applicable_chapter_end: Optional[str]
    age_description: Optional[str]
    height_cm: Optional[int]
    build_description: Optional[str]
    face_description: Optional[str]
    hair_description: Optional[str]
    costumes: Optional[dict]
    dou_qi_color: Optional[str]
    dou_qi_level: Optional[str]
    key_features: list
    reference_image_urls: list
    # 三视图
    view_front_url: Optional[str] = None
    view_side_url: Optional[str] = None
    view_back_url: Optional[str] = None
    # 状态图片
    state_images: Optional[dict] = None
    base_image_prompt: Optional[str]


class CharacterVersionBrief(BaseResponse):
    """角色版本简要响应。"""
    character_id: int
    version_code: str
    label: str
    view_front_url: Optional[str] = None


# ---------------------------------------------------------------------------
# Character
# ---------------------------------------------------------------------------

class CharacterCreate(BaseModel):
    """创建角色请求体。"""
    name: str = Field(..., max_length=50, description="角色名称")
    name_aliases: List[str] = Field(default_factory=list, description="别名列表")
    consistent_features: Optional[Dict[str, Any]] = Field(None, description="跨版本固定特征")
    expression_guide: Optional[Dict[str, Any]] = Field(None, description="表情指南字典")
    action_guide: Optional[Dict[str, Any]] = Field(None, description="动作指南字典")
    relationships: Optional[Dict[str, Any]] = Field(None, description="角色关系字典")
    role_description: Optional[str] = Field(None, description="角色简述")


class CharacterUpdate(BaseModel):
    """更新角色请求体。"""
    name: Optional[str] = Field(None, max_length=50)
    name_aliases: Optional[List[str]] = None
    consistent_features: Optional[Dict[str, Any]] = None
    expression_guide: Optional[Dict[str, Any]] = None
    action_guide: Optional[Dict[str, Any]] = None
    relationships: Optional[Dict[str, Any]] = None
    role_description: Optional[str] = None


class CharacterResponse(BaseResponse):
    """角色详情响应（不含版本列表，列表通过子路由获取）。"""
    project_id: int
    char_code: str
    name: str
    name_aliases: list
    consistent_features: Optional[dict]
    expression_guide: Optional[dict]
    action_guide: Optional[dict]
    relationships: Optional[dict]
    role_description: Optional[str]


class CharacterDetailResponse(CharacterResponse):
    """角色详情响应（含所有版本）。"""
    versions: List[CharacterVersionResponse] = []


# ---------------------------------------------------------------------------
# 预定义状态类型
# ---------------------------------------------------------------------------

CHARACTER_STATE_TYPES = {
    "anger": "愤怒",
    "happy": "开心",
    "sad": "悲伤",
    "surprise": "惊讶",
    "fear": "恐惧",
    "determination": "坚定",
    "skill_release": "释放技能",
    "battle_stance": "战斗姿态",
    "injured": "受伤",
    "exhausted": "精疲力尽",
    "meditation": "冥想",
    "triumph": "胜利",
}
