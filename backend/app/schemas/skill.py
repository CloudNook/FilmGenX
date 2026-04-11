"""
Skill 的 API 请求/响应 Schema。
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class SkillParseResult(BaseModel):
    """Markdown 解析结果（用于前端补全）。"""
    fields: Dict[str, Any] = Field(description="解析出的所有结构化字段")
    missing_fields: List[str] = Field(description="缺失的字段，前端需补全")
    warnings: List[Dict[str, str]] = Field(
        default_factory=list,
        description="解析警告（非致命）"
    )
    raw_markdown: str = Field(description="原始 Markdown 全文")


class SkillMarkdownBody(BaseModel):
    """Markdown 内容请求体。"""
    content: str = Field(..., min_length=1, description="SKILL.md 原始 Markdown 文本")


class SkillCreate(BaseModel):
    """创建 Skill 请求体（Admin 补全后提交）。"""
    name: str = Field(..., min_length=1, max_length=64, description="唯一标识（小写/数字/连字符）")
    title: Optional[str] = Field(None, max_length=128, description="人类可读标题")
    description: str = Field(..., min_length=1, description="一句话描述（Agent 激活依据）")
    content: Optional[str] = Field(None, description="核心指令（Agent 实际执行的内容）")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="JSON Schema 参数定义")
    examples: List[str] = Field(default_factory=list, description="使用示例列表")
    constraints: List[str] = Field(default_factory=list, description="约束条件列表")
    category: Optional[str] = Field(None, max_length=64, description="领域分类")
    difficulty: Optional[str] = Field(None, pattern=r"^(beginner|intermediate|advanced)$", description="难度级别")
    tags: List[str] = Field(default_factory=list, description="标签列表")
    author: Optional[str] = Field(None, max_length=64, description="作者")
    raw_markdown: Optional[str] = Field(None, description="原始 Markdown 全文")
    is_active: bool = Field(True, description="是否启用")
    skill_metadata: Dict[str, Any] = Field(default_factory=dict, alias="metadata", description="扩展元数据")


class SkillUpdate(BaseModel):
    """更新 Skill 请求体（所有字段可选，仅更新传入的字段）。"""
    title: Optional[str] = Field(None, max_length=128)
    description: Optional[str] = Field(None, min_length=1)
    content: Optional[str] = None
    parameters: Optional[Dict[str, Any]] = None
    examples: Optional[List[str]] = None
    constraints: Optional[List[str]] = None
    category: Optional[str] = Field(None, max_length=64)
    difficulty: Optional[str] = Field(None, pattern=r"^(beginner|intermediate|advanced)$")
    tags: Optional[List[str]] = None
    author: Optional[str] = Field(None, max_length=64)
    raw_markdown: Optional[str] = None
    is_active: Optional[bool] = None
    skill_metadata: Optional[Dict[str, Any]] = None


class SkillResponse(BaseModel):
    """Skill 完整响应。"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime
    name: str
    title: Optional[str]
    description: str
    content: Optional[str]
    parameters: Dict[str, Any]
    examples: List[str]
    constraints: List[str]
    category: Optional[str]
    difficulty: Optional[str]
    tags: List[str]
    author: Optional[str]
    raw_markdown: Optional[str]
    is_active: bool
    version: int
    skill_metadata: Dict[str, Any]


class SkillLiteResponse(BaseModel):
    """Skill 摘要响应（不含 content，用于 Agent 启动时注入）。"""
    model_config = ConfigDict(from_attributes=True)

    name: str
    title: Optional[str]
    description: str
    parameters: Dict[str, Any]


class SkillUploadResponse(BaseModel):
    """上传 Markdown 后的解析结果。"""
    skill: SkillParseResult = Field(description="解析结果")
    # 如果同名 Skill 已存在，返回已有数据用于 diff
    existing: Optional[SkillResponse] = Field(None, description="同名 Skill 的现有数据（如有）")
    is_update: bool = Field(False, description="是否为更新操作")


class SkillDiffResponse(BaseModel):
    """Skill 对比结果（展示新旧差异）。"""
    field: str
    old_value: Optional[Any] = None
    new_value: Optional[Any] = None
    source: str = "markdown"  # "markdown" | "existing" | "missing"
