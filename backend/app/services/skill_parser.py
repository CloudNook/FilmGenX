"""
SKILL.md 解析器（Claude 风格）。

格式约定：
- YAML frontmatter（必须以 ``---`` 起止）携带：
    - ``name``（必填，唯一标识，小写/数字/连字符）
    - ``description``（必填，"Use when ... to ..." 句式）
    - ``target_agents``（list[str]，可选；不填则不参与 L1 注入）
    - ``tags`` / ``author`` / ``metadata``（可选）
- frontmatter 之后的 markdown 主体即 ``body``，但其中所有
  ``## reference: <key>``（不区分大小写）形式的 H2 章节会被剥离到
  ``references`` 数组：``{key, title, body}``。
- 旧格式（``## content`` / ``## examples`` / ``## constraints`` / ``## parameters``）
  视为遗留，全部并入 ``body``，不再单独提取，并通过 ``warnings`` 提示 admin 迁移。

设计要点：
- 能解析多少解析多少；缺失字段写入 ``missing_fields``，不抛异常。
- ``reference key`` 强制 lower-case + ``[a-z0-9-_]``；不合法 key 走 warning + 跳过。
- ``raw_markdown`` 完整保存，前端可随时重渲染。
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Optional

import yaml

REFERENCE_HEADING_PATTERN = re.compile(
    r"^##\s+reference\s*:\s*(?P<key>[^\n]+?)\s*$",
    re.IGNORECASE | re.MULTILINE,
)
H1_PATTERN = re.compile(r"^#\s+(?P<title>.+)$", re.MULTILINE)

LEGACY_SECTION_NAMES = {"content", "examples", "constraints", "parameters"}
LEGACY_SECTION_PATTERN = re.compile(
    r"^##\s+(?P<name>content|examples|constraints|parameters)\s*$",
    re.IGNORECASE | re.MULTILINE,
)

REQUIRED_FIELDS = {"name", "description"}
ALL_FIELDS = {
    "name",
    "description",
    "target_agents",
    "tags",
    "author",
    "body",
    "references",
    "metadata",
}


@dataclass
class ParseWarning:
    field: str
    message: str


@dataclass
class ParseResult:
    """解析结果（与旧版兼容；缺失字段写 missing_fields，警告写 warnings）。"""

    fields: dict[str, Any] = field(default_factory=dict)
    missing_fields: list[str] = field(default_factory=list)
    warnings: list[ParseWarning] = field(default_factory=list)
    raw_markdown: str = ""

    def to_dict(self) -> dict:
        return {
            "fields": self.fields,
            "missing_fields": self.missing_fields,
            "warnings": [
                {"field": w.field, "message": w.message} for w in self.warnings
            ],
            "raw_markdown": self.raw_markdown,
        }


def parse_skill_markdown(raw: str) -> ParseResult:
    """主解析入口。

    流程：
    1. 拆 YAML frontmatter / body
    2. frontmatter → name / description / target_agents / tags / author / metadata
    3. body 中提取所有 ``## reference: <key>`` 章节到 references
    4. body 剩余部分（已剥离 references）作为 body 字段保存
    5. 检测旧 section（``## content`` 等）并产出 warning
    6. 校验必填字段
    """
    result = ParseResult(raw_markdown=raw)

    if not raw or not raw.strip():
        result.missing_fields = sorted(REQUIRED_FIELDS)
        return result

    frontmatter, body = _split_frontmatter(raw, result)
    _apply_frontmatter(frontmatter, result)

    references, body_clean = _extract_references(body, result)
    result.fields["references"] = references

    # body 字段最终保存"剥离 references 后"的剩余 markdown
    result.fields["body"] = body_clean.strip()

    # 旧格式 section 警告（不再支持顶层提取，并入 body）
    legacy_hits = LEGACY_SECTION_PATTERN.findall(body_clean)
    if legacy_hits:
        seen = sorted({hit.lower() for hit in legacy_hits})
        result.warnings.append(
            ParseWarning(
                field="body",
                message=(
                    f"检测到遗留 section: {', '.join(seen)}。"
                    "新版 skill 不再单独提取这些 section；"
                    "若需被 LLM 按需加载，请改写为 `## reference: <key>`，否则它们将作为 body 一部分被一次性加载。"
                ),
            )
        )

    # H1 -> 写入 metadata.title 兜底（不进 frontmatter，不当顶层字段）
    _maybe_capture_title(body_clean, result)

    # 校验必填字段
    for field_name in REQUIRED_FIELDS:
        if not result.fields.get(field_name):
            if field_name not in result.missing_fields:
                result.missing_fields.append(field_name)

    return result


# ---------------------------------------------------------------------- #
# Internals
# ---------------------------------------------------------------------- #


def _split_frontmatter(raw: str, result: ParseResult) -> tuple[dict, str]:
    """拆 YAML frontmatter / body。frontmatter 不存在时返回 ({}, raw)。"""
    stripped = raw.lstrip()
    if not stripped.startswith("---"):
        return {}, raw

    parts = stripped.split("---", 2)
    if len(parts) < 3:
        return {}, raw

    try:
        loaded = yaml.safe_load(parts[1])
    except yaml.YAMLError as exc:
        result.warnings.append(
            ParseWarning(
                field="frontmatter",
                message=f"YAML 解析失败: {exc}; 跳过 frontmatter",
            )
        )
        return {}, parts[2]

    if not isinstance(loaded, dict):
        return {}, parts[2]
    return loaded, parts[2]


def _apply_frontmatter(frontmatter: dict, result: ParseResult) -> None:
    """把 frontmatter 字段写入 result.fields。"""
    name = frontmatter.get("name")
    if isinstance(name, str) and name.strip():
        result.fields["name"] = name.strip().lower()
    else:
        result.missing_fields.append("name")

    description = frontmatter.get("description")
    if isinstance(description, str) and description.strip():
        result.fields["description"] = description.strip()
    else:
        result.missing_fields.append("description")

    target_agents = frontmatter.get("target_agents")
    if target_agents is not None:
        result.fields["target_agents"] = _coerce_str_list(
            target_agents, field_name="target_agents", result=result
        )

    tags = frontmatter.get("tags")
    if tags is not None:
        result.fields["tags"] = _coerce_str_list(
            tags, field_name="tags", result=result
        )

    author = frontmatter.get("author")
    if isinstance(author, str) and author.strip():
        result.fields["author"] = author.strip()

    metadata = frontmatter.get("metadata")
    if isinstance(metadata, dict):
        result.fields["metadata"] = metadata


def _coerce_str_list(
    value: Any, *, field_name: str, result: ParseResult
) -> list[str]:
    """把 list / 逗号串 转成 list[str]，去空 / 去重保序。"""
    if isinstance(value, list):
        items = [str(x).strip() for x in value if x is not None]
    elif isinstance(value, str):
        items = [t.strip() for t in re.split(r"[,，]", value) if t.strip()]
    else:
        result.warnings.append(
            ParseWarning(
                field=field_name,
                message=f"{field_name} 应为 list 或逗号分隔字符串；忽略 {type(value).__name__}",
            )
        )
        return []

    seen: set[str] = set()
    deduped: list[str] = []
    for item in items:
        if item and item not in seen:
            seen.add(item)
            deduped.append(item)
    return deduped


def _extract_references(body: str, result: ParseResult) -> tuple[list[dict], str]:
    """从 body 中提取 ``## reference: <key>`` 章节。

    返回：``(references, body_without_references)``
    """
    matches = list(REFERENCE_HEADING_PATTERN.finditer(body))
    if not matches:
        return [], body

    references: list[dict] = []
    seen_keys: set[str] = set()
    # 我们保留原 body 但删除 references 段的范围；用 (start, end) 标记需要删除的区间
    cuts: list[tuple[int, int]] = []

    for idx, match in enumerate(matches):
        key = match.group("key").strip().lower()
        # heading 行的起点
        section_start = match.start()
        # 章节正文从 heading 末尾开始；正文止于下一段 ``## reference:`` 或 body 结尾
        body_start = match.end()
        body_end = matches[idx + 1].start() if idx + 1 < len(matches) else len(body)

        ref_body = body[body_start:body_end].lstrip("\n").rstrip()
        if not _is_valid_ref_key(key):
            result.warnings.append(
                ParseWarning(
                    field="references",
                    message=f"非法 reference key: '{key}'; 仅允许 [a-z0-9-_]，已跳过",
                )
            )
            continue
        if key in seen_keys:
            result.warnings.append(
                ParseWarning(
                    field="references",
                    message=f"重复的 reference key: '{key}'; 后出现的版本将覆盖前者",
                )
            )

        references.append(
            {
                "key": key,
                "title": _heading_to_title(key),
                "body": ref_body,
            }
        )
        seen_keys.add(key)
        cuts.append((section_start, body_end))

    # 按倒序删除区间，保持索引有效
    body_clean = body
    for start, end in reversed(cuts):
        body_clean = body_clean[:start] + body_clean[end:]

    # 同 key 后者覆盖前者（保留最后一份）
    if len({r["key"] for r in references}) != len(references):
        deduped: dict[str, dict] = {}
        for ref in references:
            deduped[ref["key"]] = ref
        references = list(deduped.values())

    return references, body_clean


_VALID_REF_KEY = re.compile(r"^[a-z0-9][a-z0-9_-]*$")


def _is_valid_ref_key(key: str) -> bool:
    return bool(_VALID_REF_KEY.match(key))


def _heading_to_title(key: str) -> str:
    """从 key 推一个人类可读 title（不影响 LLM，只用于前端展示）。"""
    return key.replace("-", " ").replace("_", " ").strip().title()


def _maybe_capture_title(body: str, result: ParseResult) -> None:
    """body 第一个 H1 作为 metadata.title 兜底（不写到顶层字段）。"""
    if "metadata" in result.fields and "title" in result.fields["metadata"]:
        return
    h1 = H1_PATTERN.search(body)
    if not h1:
        return
    title = h1.group("title").strip()
    metadata = result.fields.setdefault("metadata", {})
    if isinstance(metadata, dict) and "title" not in metadata:
        metadata["title"] = title
