"""
GeminiLLMExtractor —— 实现 ``MemoryExtractor`` Protocol。

**只抽 preference / outline 两种 kind**。其它 kind（character / scene / style / script）
全部走"agent 通过 memory_save 工具显式写入"——LLM 看到工具结果（OSS URL 等）后
主动调 memory_save 才入库。这样：
- LLM 不会乱发明 entity_key / entity_kind（比如不同会话给同一角色起 4 个 key）
- 只有"对话里能挖出的软信息"（preference / outline）走自动抽取

response_schema 结构化输出 + per-kind value 字段，让 Gemini 直接产出与 taxonomy
对齐的结构。下游 provider 还会再走一次 ``validate_kv`` 兜底。
"""

from __future__ import annotations

import json
import logging
from typing import Any, Literal, Optional

from google import genai
from google.genai import types as genai_types
from pydantic import BaseModel, Field

from app.core.agent.memory.extractor import MemoryExtractor
from app.core.agent.memory.types import CandidateMemory
from app.core.config import settings

logger = logging.getLogger(__name__)


DEFAULT_EXTRACT_MODEL = "gemini-3-flash-preview"


# ---- LLM response_schema ------------------------------------------------ #


class _PreferenceItem(BaseModel):
    """与 ``app.memory.taxonomy.PreferenceValue`` 对齐 + 限定 key 的 enum。"""

    key: Literal["genre", "duration", "pacing", "format", "structure"] = Field(
        ..., description="偏好维度"
    )
    description: str = Field(..., description="该偏好的具体描述")
    confidence: float = Field(default=0.8, ge=0.0, le=1.0)


class _OutlineItem(BaseModel):
    """与 ``app.memory.taxonomy.OutlineValue`` 对齐。一份 outline 一个 project。"""

    summary: str = Field(..., description="一句话剧情综述")
    characters: list[str] = Field(default_factory=list, description="主要角色名清单")
    key_arcs: list[str] = Field(default_factory=list, description="关键情节段落")
    duration_seconds: Optional[int] = Field(default=None, description="预期总时长（秒）")
    confidence: float = Field(default=0.8, ge=0.0, le=1.0)


class _ExtractedOutput(BaseModel):
    """整体输出。preference 可多条；outline 至多一份。"""

    preferences: list[_PreferenceItem] = Field(
        default_factory=list,
        description="抽出的用户偏好。一个偏好维度不重复出现；不确定就不抽。",
    )
    outline: Optional[_OutlineItem] = Field(
        default=None,
        description="项目大纲。只有当对话里出现完整剧情大纲讨论时才抽，否则留空。",
    )


_DEFAULT_SYSTEM_PROMPT = """你是 FilmGenX 项目的 memory 抽取助手。从对话片段中识别"值得跨会话记忆的软信息"，输出结构化候选。

# 你只抽两种内容
1. **preference**：用户对作品的明确偏好。维度限定为 5 个：
   - genre（题材：科幻/玄幻/都市…）
   - duration（时长：60秒/3分钟…）
   - pacing（节奏：快节奏/慢热…）
   - format（剧本格式：含镜头号/旁白…）
   - structure（结构：起承转合时间分配…）
   每个维度只产出一条，描述清楚即可。

2. **outline**：项目级剧情大纲。一个 project 只一份。
   仅当用户/agent 给出完整剧情大纲讨论（不是片段台词）时抽出。
   字段：summary（一句话）、characters（主要角色名）、key_arcs（关键情节段）、duration_seconds（总时长秒）。

# 你不抽什么
- character（角色）/ scene（场景）/ style（视觉风格）/ script（剧本）：这些由 agent 调
  memory_save 工具显式写入；你不要碰这些 kind。
- 闲聊 / 临时讨论 / 过程性思考 / reviewer 中间态。
- 用户没明确表态的内容。宁可不抽，不要硬猜。

# 重要约束
- 只输出 schema 里定义的字段，不要发明新字段。
- 不要重复抽：同一 preference 维度只出现一次。
- 没什么可抽就返回空数组 / outline=null。
"""


class GeminiLLMExtractor(MemoryExtractor):
    """实现 ``MemoryExtractor`` Protocol。"""

    def __init__(
        self,
        *,
        model: str = DEFAULT_EXTRACT_MODEL,
        system_prompt: str = _DEFAULT_SYSTEM_PROMPT,
    ) -> None:
        self._model = model
        self._system_prompt = system_prompt
        self._client: Optional[genai.Client] = None

    def _get_client(self) -> genai.Client:
        if self._client is None:
            if not settings.GOOGLE_API_KEY:
                raise RuntimeError(
                    "GOOGLE_API_KEY 未配置（请检查 .env）；"
                    "GeminiLLMExtractor 需要 API key"
                )
            self._client = genai.Client(api_key=settings.GOOGLE_API_KEY)
        return self._client

    async def extract(
        self,
        messages: list[dict[str, Any]],
        scope_metadata: dict[str, Any],
    ) -> list[CandidateMemory]:
        if not messages:
            return []

        client = self._get_client()
        conversation = _format_messages(messages)
        scope_summary = _format_scope(scope_metadata)

        user_prompt = (
            f"## 当前 scope\n{scope_summary}\n\n"
            f"## 对话片段\n{conversation}\n\n"
            "请按 schema 输出 preference / outline 候选条目。"
        )

        config = genai_types.GenerateContentConfig(
            system_instruction=self._system_prompt,
            response_mime_type="application/json",
            response_schema=_strip_unsupported(_ExtractedOutput.model_json_schema()),
            temperature=0.2,
        )

        try:
            response = await client.aio.models.generate_content(
                model=self._model,
                contents=user_prompt,
                config=config,
            )
        except Exception:
            logger.exception("[gemini-extractor] generate_content failed")
            return []

        raw_text = (response.text or "").strip()
        if not raw_text:
            return []

        try:
            payload = json.loads(raw_text)
            parsed = _ExtractedOutput.model_validate(payload)
        except Exception:
            logger.exception(
                "[gemini-extractor] failed to parse LLM JSON output: %r",
                raw_text[:300],
            )
            return []

        candidates: list[CandidateMemory] = []
        meta_base = {"extractor": "gemini_llm", "model": self._model}

        for pref in parsed.preferences:
            candidates.append(
                CandidateMemory(
                    content=pref.description,
                    kind="preference",
                    entity={
                        "entity_kind": "preference",
                        "entity_key": pref.key,
                        "description": pref.description,
                    },
                    confidence=pref.confidence,
                    extraction_metadata=dict(meta_base),
                )
            )

        if parsed.outline is not None:
            ol = parsed.outline
            outline_value = {
                "summary": ol.summary,
                "characters": list(ol.characters),
                "key_arcs": list(ol.key_arcs),
                "duration_seconds": ol.duration_seconds,
            }
            candidates.append(
                CandidateMemory(
                    content=ol.summary,
                    kind="outline",
                    entity={
                        "entity_kind": "outline",
                        "entity_key": "main",
                        **outline_value,
                    },
                    confidence=ol.confidence,
                    extraction_metadata=dict(meta_base),
                )
            )

        logger.info(
            "[gemini-extractor] extracted %d candidate(s) from %d message(s) "
            "(preference=%d, outline=%s)",
            len(candidates),
            len(messages),
            len(parsed.preferences),
            "yes" if parsed.outline else "no",
        )
        return candidates


def _strip_unsupported(schema: Any) -> Any:
    """剥掉 Gemini response_schema 不识别的 JSON Schema 关键字。

    Pydantic 默认输出 ``additionalProperties`` / ``$defs`` / ``title`` 等；Gemini 的
    structured output 是 JSON Schema 的子集，遇到不识别的字段会 400。简单地把这些
    递归删掉即可。
    """
    blocked = {"additionalProperties", "$schema", "title", "examples"}
    if isinstance(schema, dict):
        return {k: _strip_unsupported(v) for k, v in schema.items() if k not in blocked}
    if isinstance(schema, list):
        return [_strip_unsupported(item) for item in schema]
    return schema


def _format_messages(messages: list[dict[str, Any]]) -> str:
    lines: list[str] = []
    for m in messages:
        role = m.get("role", "?")
        content = m.get("content", "")
        if not content:
            continue
        lines.append(f"[{role}]\n{content}")
    return "\n\n".join(lines)


def _format_scope(scope_metadata: dict[str, Any]) -> str:
    if not scope_metadata:
        return "(empty)"
    return ", ".join(f"{k}={v}" for k, v in scope_metadata.items())
