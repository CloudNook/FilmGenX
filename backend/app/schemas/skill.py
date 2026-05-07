"""
Skill 的 API 请求/响应 Schema（Claude SKILL.md 风格）。
"""

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------- #
# 子结构
# ---------------------------------------------------------------------- #


class SkillReferenceItem(BaseModel):
    """单个 reference 子文档。"""

    key: str = Field(..., min_length=1, description="reference key（[a-z0-9_-]）")
    title: str = Field("", description="人类可读标题，前端展示用")
    body: str = Field("", description="reference body markdown")


class LintIssueResponse(BaseModel):
    """lint 输出条目。"""

    level: Literal["error", "warning"]
    code: str
    message: str
    field: str
    token: Optional[str] = None


# ---------------------------------------------------------------------- #
# 上传 / 解析 / 预览
# ---------------------------------------------------------------------- #


class SkillParseResult(BaseModel):
    """Markdown 解析结果（用于前端补全）。"""

    fields: Dict[str, Any] = Field(description="解析出的所有结构化字段")
    missing_fields: List[str] = Field(description="缺失的必填字段，前端需补全")
    warnings: List[Dict[str, str]] = Field(
        default_factory=list,
        description="解析警告（非致命）",
    )
    raw_markdown: str = Field(description="原始 Markdown 全文")


class SkillMarkdownBody(BaseModel):
    """Markdown 内容请求体。"""

    content: str = Field(..., min_length=1, description="SKILL.md 原始 Markdown 文本")


# ---------------------------------------------------------------------- #
# CRUD 请求体
# ---------------------------------------------------------------------- #


class SkillCreate(BaseModel):
    """创建 Skill 请求体。"""

    name: str = Field(
        ..., min_length=1, max_length=64, description="唯一标识（小写/数字/连字符）"
    )
    description: str = Field(
        ...,
        min_length=1,
        description="激活条件，建议 'Use when ... to ...' 句式",
    )
    target_agents: List[str] = Field(
        default_factory=list,
        description="此 skill 适用的 sub-agent 列表，L1 注入按 agent 名反查",
    )
    body: Optional[str] = Field(
        None, description="SKILL.md body markdown（L2 主体）"
    )
    references: List[SkillReferenceItem] = Field(
        default_factory=list,
        description="reference 子文档列表（L3）",
    )
    tags: List[str] = Field(default_factory=list, description="标签列表")
    author: Optional[str] = Field(None, max_length=64, description="作者")
    raw_markdown: Optional[str] = Field(None, description="原始 Markdown 全文")
    is_active: bool = Field(True, description="是否启用")
    skill_metadata: Dict[str, Any] = Field(
        default_factory=dict,
        alias="metadata",
        description="扩展元数据",
    )


class SkillUpdate(BaseModel):
    """更新 Skill 请求体（仅更新非 None 字段）。"""

    description: Optional[str] = Field(None, min_length=1)
    target_agents: Optional[List[str]] = None
    body: Optional[str] = None
    references: Optional[List[SkillReferenceItem]] = None
    tags: Optional[List[str]] = None
    author: Optional[str] = Field(None, max_length=64)
    raw_markdown: Optional[str] = None
    is_active: Optional[bool] = None
    skill_metadata: Optional[Dict[str, Any]] = None


# ---------------------------------------------------------------------- #
# 响应
# ---------------------------------------------------------------------- #


class SkillResponse(BaseModel):
    """Skill 完整响应。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime
    name: str
    description: str
    target_agents: List[str]
    body: Optional[str]
    references: List[SkillReferenceItem]
    tags: List[str]
    author: Optional[str]
    raw_markdown: Optional[str]
    is_active: bool
    version: int
    skill_metadata: Dict[str, Any]


class SkillMetaResponse(BaseModel):
    """Skill L1 元信息响应（不含 body / references）。

    用于 admin picker / agent 启动时注入 system prompt。
    """

    model_config = ConfigDict(from_attributes=True)

    name: str
    description: str
    target_agents: List[str]
    tags: List[str]


class SkillUploadResponse(BaseModel):
    """上传 Markdown 后的解析结果。"""

    skill: SkillParseResult = Field(description="解析结果")
    existing: Optional[SkillResponse] = Field(
        None, description="同名 Skill 的现有数据（如有）"
    )
    is_update: bool = Field(False, description="是否为更新操作")


class SkillLintResponse(BaseModel):
    """Lint 端点响应。"""

    skill_name: str
    issues: List[LintIssueResponse]
