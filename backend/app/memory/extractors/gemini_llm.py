"""
GeminiLLMExtractor —— 实现 ``MemoryExtractor`` Protocol。

把原始消息序列喂给 Gemini，让它抽出"值得记的事实/偏好/决策"。LLM 返回结构化
JSON（按 schema 强约束），每条对应一个 ``CandidateMemory``。

抽取出来的 candidate 后续走 framework 的 post-extraction filter chain，所以这里
不需要做去重 / 质量评估 —— 只管"用 LLM 把对话压成结构化候选"。

业务可以自己写更高级的 Extractor（比如规则式 + LLM 兜底），实现同样的 Protocol 即可。
"""

from __future__ import annotations

import json
import logging
from typing import Any, Optional

from google import genai
from google.genai import types as genai_types
from pydantic import BaseModel, Field

from app.core.agent.memory.extractor import MemoryExtractor
from app.core.agent.memory.types import CandidateMemory
from app.core.config import settings

logger = logging.getLogger(__name__)


DEFAULT_EXTRACT_MODEL = "gemini-3-flash-preview"  # 抽取用便宜模型


# ---- LLM 输出 schema（response_schema 强约束）----


class _ExtractedMemoryItem(BaseModel):
    """LLM 抽取出的单条候选 —— 与 CandidateMemory 字段对齐。"""

    content: str = Field(..., description="自然语言陈述：1-2 句话，可直接读")
    kind: str = Field(
        ...,
        description=(
            "条目类型，从 fact / preference / decision / episode_outcome 中选。"
            "fact = 客观事实；preference = 用户偏好；decision = 关键决定；"
            "episode_outcome = 集级结尾状态 / 伏笔"
        ),
    )
    confidence: float = Field(
        default=0.8,
        ge=0.0,
        le=1.0,
        description="置信度 0-1，模糊或推断时降低",
    )
    entity_kind: Optional[str] = Field(
        default=None,
        description=(
            "如果这条是关于某个具体实体（角色 / 场景 / asset / 用户偏好）的当前态，"
            "在这里写实体类型，如 character / scene / preference。否则留空。"
        ),
    )
    entity_key: Optional[str] = Field(
        default=None,
        description=(
            "实体的业务 key（角色名 / 场景名 / 偏好 key）。entity_kind 非空时必填，"
            "否则留空。"
        ),
    )


class _ExtractedMemoryList(BaseModel):
    items: list[_ExtractedMemoryItem] = Field(
        default_factory=list,
        description="抽出的候选条目列表；没什么值得记的就返回空数组",
    )


_DEFAULT_SYSTEM_PROMPT = """你是一个 memory 抽取助手。从给定的对话片段中识别"值得跨会话记忆的内容"，输出结构化候选条目。

判定标准（满足任一即可抽出）：
- 客观事实：项目 / 用户身上稳定不变的属性
- 用户偏好：用户明确说"我喜欢/不喜欢/总是这样做"
- 关键决定：影响后续工作的决策（"用 photorealistic 风格"）
- 集级结尾 / 伏笔：跨会话还会被引用的剧情节点

不要抽：闲聊、临时讨论、过程性思考、reviewer 反复修订的中间产物。

如果某条信息是关于一个具体实体的当前态（"陈墨的最新设定"、"用户的色调偏好"），
填写 entity_kind + entity_key，下游会把它存到实体表（profile）做精确召回。
否则留空，存到事件表（memory）做语义召回。

实体识别规则：
- character / 角色：entity_key = 角色名
- scene / 场景：entity_key = 地点名
- preference / 偏好：entity_key = 偏好领域（如 dialog_length / color_palette）
- visual_style / 风格锚：entity_key = 风格 ID
- asset / 已生成素材：entity_key = 资产业务 key

宁可抽取保守一些少几条，不要把不确定的内容硬抽成"事实"。
"""


class GeminiLLMExtractor(MemoryExtractor):
    """实现 ``MemoryExtractor`` Protocol。"""

    def __init__(
        self,
        *,
        model: str = DEFAULT_EXTRACT_MODEL,
        system_prompt: str = _DEFAULT_SYSTEM_PROMPT,
    ) -> None:
        """API key 走 ``settings.GOOGLE_API_KEY``（``.env`` 配置），不显式传。"""
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
            "请按 schema 输出值得记的候选条目。"
        )

        config = genai_types.GenerateContentConfig(
            system_instruction=self._system_prompt,
            response_mime_type="application/json",
            response_schema=_ExtractedMemoryList.model_json_schema(),
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
            parsed = _ExtractedMemoryList.model_validate(payload)
        except Exception:
            logger.exception(
                "[gemini-extractor] failed to parse LLM JSON output: %r",
                raw_text[:300],
            )
            return []

        candidates: list[CandidateMemory] = []
        for item in parsed.items:
            entity: Optional[dict[str, Any]] = None
            if item.entity_kind and item.entity_key:
                entity = {
                    "entity_kind": item.entity_kind,
                    "entity_key": item.entity_key,
                }
            candidates.append(
                CandidateMemory(
                    content=item.content,
                    kind=item.kind,
                    entity=entity,
                    confidence=item.confidence,
                    extraction_metadata={
                        "extractor": "gemini_llm",
                        "model": self._model,
                    },
                )
            )

        logger.info(
            "[gemini-extractor] extracted %d candidate(s) from %d message(s)",
            len(candidates),
            len(messages),
        )
        return candidates


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
