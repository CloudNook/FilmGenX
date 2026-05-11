"""
FilmGenX 项目级 KV memory 的业务 taxonomy。

framework 不感知任何具体 kind / key —— 这份 taxonomy 完全是 FilmGenX 业务定义。
其它业务可以在自己的 ``app/memory/`` 下定义不同的 taxonomy。

设计原则：
- ``kind`` 是闭集：character / scene / style / preference / outline / script。Agent 不能
  发明新 kind；extractor / memory_save 工具的 schema 把 kind 锁死成 enum。
- ``key`` 按 kind 分两类：
  - **open key**: character / scene —— key 是 canonical 实体名（角色名 / 场景名）。
    业务实体动态展开，但每个实体名只有一行 active 记录（UPSERT 语义）。
  - **closed key**: style / preference —— key 必须从 enum 里选。
  - **single key**: outline / script —— key 永远是 ``"main"``，一个 project 一份。
- ``value`` 是结构化 Pydantic 模型，不是 free-form 文本摘要。下游 agent 直接消费字段。

写入路径分两路：
- **业务工具直接写**（确定性）：``generate_image`` 出图后，agent 把返回的 OSS URL 通过
  ``memory_save`` 写入 ``character.{name}.three_view_url``。无 LLM "提取"。
- **LLM extractor 写**（辅助）：从对话里挖 ``preference.*`` / ``outline.main`` 这种"软"
  信息。Extractor 输出 schema 受 taxonomy 强约束，不在表里的 kind 直接拒收。
"""

from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


# --------------------------------------------------------------------- #
# 各 kind 的 value 结构（精确 schema，不是 free-form summary）
# --------------------------------------------------------------------- #


class CharacterValue(BaseModel):
    """角色 KV 的 value。key = canonical 角色名（如 "萧炎"）。"""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(..., description="canonical 角色名，与 key 对齐")
    role: Optional[str] = Field(None, description="protagonist | antagonist | supporting")
    appearance: Optional[str] = Field(None, description="外貌设定（发型 / 体型 / 服装核心特征）")
    personality: Optional[str] = Field(None, description="性格描述")
    key_skills: list[str] = Field(default_factory=list, description="招式 / 能力清单")
    backstory: Optional[str] = Field(None, description="背景故事关键节点")
    three_view_asset_code: Optional[str] = Field(
        None,
        description="三视图 asset_code（由 generate_image 出图后保存到 assets 表，code 是稳定句柄）",
    )
    reference_asset_codes: list[str] = Field(
        default_factory=list,
        description="其它参考图 asset_code 列表（表情 / 服装变体 / 战斗姿态 等）",
    )


class SceneValue(BaseModel):
    """场景 KV 的 value。key = canonical 场景名（如 "云岚宗广场"）。"""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(..., description="canonical 场景名，与 key 对齐")
    location_description: Optional[str] = Field(None, description="地点 / 建筑特征")
    atmosphere: Optional[str] = Field(None, description="氛围 / 情绪基调")
    lighting: Optional[str] = Field(None, description="光照设定")
    props: list[str] = Field(default_factory=list, description="关键道具")
    reference_asset_codes: list[str] = Field(
        default_factory=list, description="场景参考图 asset_code 列表"
    )


# style 的 5 个 closed sub-key，value 共用一份单字段 schema
StyleSubKey = Literal["palette", "lighting", "composition", "mood", "camera"]


class StyleValue(BaseModel):
    """视觉风格锚点 KV 的 value。key 从 ``StyleSubKey`` enum 选。"""

    model_config = ConfigDict(extra="forbid")

    description: str = Field(..., description="该 style sub-key 的具体描述")
    keywords: list[str] = Field(default_factory=list, description="便于复用的关键词")


# preference 的 closed sub-key
PreferenceSubKey = Literal["genre", "duration", "pacing", "format", "structure"]


class PreferenceValue(BaseModel):
    """用户偏好 KV 的 value。key 从 ``PreferenceSubKey`` enum 选。"""

    model_config = ConfigDict(extra="forbid")

    description: str = Field(..., description="该偏好的具体描述")


class OutlineValue(BaseModel):
    """项目大纲 KV 的 value。key 永远是 ``"main"``。"""

    model_config = ConfigDict(extra="forbid")

    summary: str = Field(..., description="一句话剧情综述")
    characters: list[str] = Field(default_factory=list, description="主要角色名清单")
    key_arcs: list[str] = Field(default_factory=list, description="关键情节段落")
    duration_seconds: Optional[int] = Field(None, description="预期总时长（秒）")


class ScriptValue(BaseModel):
    """剧本 KV 的 value。key 永远是 ``"main"``。"""

    model_config = ConfigDict(extra="forbid")

    summary: str = Field(..., description="剧本概览")
    scene_count: Optional[int] = Field(None, description="场景数")
    total_duration_seconds: Optional[int] = Field(None, description="总时长（秒）")
    famous_quotes: list[str] = Field(default_factory=list, description="保留的金句台词")


# --------------------------------------------------------------------- #
# Kind 注册表
# --------------------------------------------------------------------- #


KindKeyKind = Literal["open", "closed", "single"]


class KindSpec(BaseModel):
    """一个 kind 的 schema 描述，registry 用。"""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    name: str
    description: str
    value_schema: type[BaseModel]
    key_kind: KindKeyKind
    allowed_keys: Optional[list[str]] = None  # closed / single 时必填

    def validate_key(self, key: str) -> None:
        if self.key_kind == "single":
            if key != "main":
                raise ValueError(
                    f"kind={self.name!r} requires key=='main' (got {key!r})"
                )
            return
        if self.key_kind == "closed":
            assert self.allowed_keys is not None
            if key not in self.allowed_keys:
                raise ValueError(
                    f"kind={self.name!r} key must be one of {self.allowed_keys} (got {key!r})"
                )
            return
        # open: 任何非空 string 都行
        if not isinstance(key, str) or not key.strip():
            raise ValueError(f"kind={self.name!r} requires a non-empty string key")

    def validate_value(self, value: dict[str, Any]) -> dict[str, Any]:
        """用 Pydantic schema 校验 value，返回归一化后的 dict。"""
        return self.value_schema.model_validate(value).model_dump(exclude_none=False)


KIND_REGISTRY: dict[str, KindSpec] = {
    "character": KindSpec(
        name="character",
        description=(
            "角色资产：每个出场角色一行；key = canonical 角色名（如 '萧炎'）。"
            "存外貌 / 性格 / 招式 / 三视图 URL 等，给后续 character_ref / frame_prompt agent 复用。"
        ),
        value_schema=CharacterValue,
        key_kind="open",
    ),
    "scene": KindSpec(
        name="scene",
        description=(
            "场景资产：每个出场场景一行；key = canonical 场景名（如 '云岚宗广场'）。"
            "存环境 / 氛围 / 光照 / 参考图 URL，给 scene_ref / frame_prompt agent 复用。"
        ),
        value_schema=SceneValue,
        key_kind="open",
    ),
    "style": KindSpec(
        name="style",
        description=(
            "全片视觉锚点：5 个固定子项（palette / lighting / composition / mood / camera）。"
            "每个子项一行，key 必须是这 5 个字符串之一。"
        ),
        value_schema=StyleValue,
        key_kind="closed",
        allowed_keys=["palette", "lighting", "composition", "mood", "camera"],
    ),
    "preference": KindSpec(
        name="preference",
        description=(
            "用户对作品的偏好：5 个固定维度（genre / duration / pacing / format / structure）。"
            "key 必须是这 5 个字符串之一。"
        ),
        value_schema=PreferenceValue,
        key_kind="closed",
        allowed_keys=["genre", "duration", "pacing", "format", "structure"],
    ),
    "outline": KindSpec(
        name="outline",
        description="项目大纲：一个 project 一份，key 固定 'main'。outline_agent 完成后写入。",
        value_schema=OutlineValue,
        key_kind="single",
        allowed_keys=["main"],
    ),
    "script": KindSpec(
        name="script",
        description="项目剧本：一个 project 一份，key 固定 'main'。script_agent 完成后写入。",
        value_schema=ScriptValue,
        key_kind="single",
        allowed_keys=["main"],
    ),
}


ALLOWED_KINDS: list[str] = list(KIND_REGISTRY.keys())


def validate_kv(kind: str, key: str, value: dict[str, Any]) -> dict[str, Any]:
    """业务侧统一入口：校验 (kind, key, value) 是否符合 taxonomy。

    返回归一化后的 value dict（Pydantic 解析后的字段）。不符合的抛 ``ValueError``。
    """
    spec = KIND_REGISTRY.get(kind)
    if spec is None:
        raise ValueError(
            f"unknown kind={kind!r}; allowed={ALLOWED_KINDS}"
        )
    spec.validate_key(key)
    return spec.validate_value(value)


def taxonomy_prompt_block() -> str:
    """喂给 LLM 的 taxonomy 描述（extractor / memory_save 工具 prompt 共用）。

    每个 kind 列出：key 规则 + **必填字段** + 可选字段。LLM 拿到这份就该知道
    哪些字段不能省（漏 required 字段的 memory_save 会被 provider 拒收）。
    """
    lines = ["## Memory Taxonomy（FilmGenX 闭集，禁止发明新 kind / key）"]
    for spec in KIND_REGISTRY.values():
        line = f"- **{spec.name}** — {spec.description}"
        if spec.key_kind == "closed":
            line += f" 允许 key: {spec.allowed_keys}。"
        elif spec.key_kind == "single":
            line += " key 固定 'main'。"
        else:
            line += " key 是开放的实体名 string。"

        required_fields: list[str] = []
        optional_fields: list[str] = []
        for field_name, field_info in spec.value_schema.model_fields.items():
            if field_info.is_required():
                required_fields.append(field_name)
            else:
                optional_fields.append(field_name)
        line += f" value 必填字段: {required_fields}"
        if optional_fields:
            line += f"；可选字段: {optional_fields}"
        lines.append(line)
    return "\n".join(lines)
