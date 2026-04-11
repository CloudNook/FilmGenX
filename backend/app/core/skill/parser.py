"""
Markdown 解析器。

将 SKILL.md 格式的 Markdown 文本解析为结构化字段。
对齐 Anthropic SKILL.md 标准：
https://www.mintlify.com/anthropics/skills/spec/skill-format

解析规则：
- YAML frontmatter → name, title, description, category, difficulty, tags, author, metadata
- ## description → 扩展描述
- ## content → 核心指令
- ## parameters → JSON code block 解析
- ## examples → 列表项解析
- ## constraints → 列表项解析
- ## metadata → JSON code block 解析
"""

import json
import re
from dataclasses import dataclass, field
from typing import Any, Optional

import yaml


@dataclass
class ParseWarning:
    """解析警告，记录非致命的解析问题。"""
    field: str
    message: str


@dataclass
class ParseResult:
    """
    解析结果。

    fields: 解析出的所有结构化字段（不含 name）
    missing_fields: 未找到的必填字段（前端需补全）
    warnings: 解析过程中的警告（非致命）
    raw_markdown: 原始 Markdown 全文
    """
    fields: dict[str, Any] = field(default_factory=dict)
    missing_fields: list[str] = field(default_factory=list)
    warnings: list[ParseWarning] = field(default_factory=list)
    raw_markdown: str = ""

    def to_dict(self) -> dict:
        return {
            "fields": self.fields,
            "missing_fields": self.missing_fields,
            "warnings": [{"field": w.field, "message": w.message} for w in self.warnings],
            "raw_markdown": self.raw_markdown,
        }


# 必填字段集合
REQUIRED_FIELDS = {"name", "description"}
# 所有可解析字段
ALL_FIELDS = {
    "name", "title", "description", "content",
    "parameters", "examples", "constraints",
    "category", "difficulty", "tags", "author",
    "metadata",
}


def parse_skill_markdown(raw: str) -> ParseResult:
    """
    解析 SKILL.md Markdown 文本，返回结构化 ParseResult。

    策略：能解析多少解析多少，缺的字段记录到 missing_fields，
    不因解析错误中断。

    Args:
        raw: SKILL.md 原始文本

    Returns:
        ParseResult，包含解析字段、缺失字段、警告
    """
    result = ParseResult()
    result.raw_markdown = raw

    if not raw or not raw.strip():
        result.missing_fields = list(REQUIRED_FIELDS)
        return result

    # === 1. 分离 YAML frontmatter 和 body ===
    frontmatter: dict[str, Any] = {}
    body: str = raw

    if raw.lstrip().startswith("---"):
        parts = raw.lstrip().split("---", 2)
        if len(parts) >= 3:
            try:
                frontmatter = yaml.safe_load(parts[1]) or {}
                body = parts[2]
            except yaml.YAMLError as e:
                result.warnings.append(ParseWarning(
                    field="frontmatter",
                    message=f"YAML 解析失败: {e}，将跳过 frontmatter"
                ))

    # === 2. 解析 frontmatter 字段 ===
    if not isinstance(frontmatter, dict):
        frontmatter = {}

    # name（必填）
    name = frontmatter.get("name")
    if name and isinstance(name, str):
        result.fields["name"] = name.strip().lower()
    else:
        result.missing_fields.append("name")

    # title（可选）
    title = frontmatter.get("title")
    if title and isinstance(title, str):
        result.fields["title"] = title.strip()

    # description（必填，优先级：frontmatter > body ## description）
    description = frontmatter.get("description")
    if description and isinstance(description, str):
        result.fields["description"] = description.strip()

    # category
    category = frontmatter.get("category")
    if category and isinstance(category, str):
        result.fields["category"] = category.strip()

    # difficulty
    difficulty = frontmatter.get("difficulty")
    if difficulty and isinstance(difficulty, str):
        result.fields["difficulty"] = difficulty.strip()

    # tags
    tags = frontmatter.get("tags")
    if tags:
        if isinstance(tags, list):
            result.fields["tags"] = [str(t).strip() for t in tags if t]
        elif isinstance(tags, str):
            result.fields["tags"] = [t.strip() for t in re.split(r"[,，]", tags) if t.strip()]

    # author
    author = frontmatter.get("author")
    if author and isinstance(author, str):
        result.fields["author"] = author.strip()

    # metadata（扩展元数据）
    metadata = frontmatter.get("metadata")
    if metadata and isinstance(metadata, dict):
        result.fields["metadata"] = metadata

    # === 3. 解析 body sections ===
    sections = _extract_sections(body)

    # ## description（覆盖 frontmatter.description）
    if "description" in sections:
        text = sections["description"].strip()
        if text:
            result.fields["description"] = text
        # 移除 missing 中的 description（因为 body 中找到了）
        if "description" in result.missing_fields:
            result.missing_fields.remove("description")

    # ## content
    if "content" in sections:
        result.fields["content"] = sections["content"].strip()

    # ## parameters（JSON code block）
    if "parameters" in sections:
        result.fields["parameters"] = _parse_json_block(
            sections["parameters"],
            result,
            "parameters",
        )

    # ## examples（Markdown 列表）
    if "examples" in sections:
        result.fields["examples"] = _parse_list_items(sections["examples"])

    # ## constraints（Markdown 列表）
    if "constraints" in sections:
        result.fields["constraints"] = _parse_list_items(sections["constraints"])

    # ## metadata（JSON code block）
    if "metadata" in sections and "metadata" not in result.fields:
        result.fields["metadata"] = _parse_json_block(
            sections["metadata"],
            result,
            "metadata",
        )

    # === 4. 从 H1 标题提取 title（fallback）===
    if "title" not in result.fields:
        h1 = re.search(r"^#\s+(.+)$", body, re.MULTILINE)
        if h1:
            result.fields["title"] = h1.group(1).strip()

    # === 5. 补全 missing_fields（必填但未找到）===
    for field_name in REQUIRED_FIELDS:
        if field_name not in result.fields or not result.fields[field_name]:
            if field_name not in result.missing_fields:
                result.missing_fields.append(field_name)

    return result


def _extract_sections(body: str) -> dict[str, str]:
    """
    从 Markdown body 中提取所有 ## section。

    返回 {"description": "...", "content": "...", ...}
    支持嵌套内容（直到遇到下一个 ## 标题或文件末尾）。
    """
    sections: dict[str, str] = {}

    # 匹配 ## 标题行，捕获标题文本
    pattern = re.compile(r"^##\s+(.+)$", re.MULTILINE)

    matches = list(pattern.finditer(body))
    for i, match in enumerate(matches):
        title = match.group(1).strip().lower().replace(" ", "-")
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(body)
        sections[title] = body[start:end].lstrip("\n")

    return sections


def _parse_json_block(text: str, result: ParseResult, field_name: str) -> Any:
    """尝试解析 text 中的 JSON code block。"""
    json_text = _extract_code_block(text, "json")
    if json_text is None:
        # 尝试直接解析整个 text
        json_text = text.strip()

    try:
        return json.loads(json_text)
    except json.JSONDecodeError as e:
        result.warnings.append(ParseWarning(
            field=field_name,
            message=f"JSON 解析失败: {e}，将使用空对象",
        ))
        return {} if field_name == "parameters" else {}


def _extract_code_block(text: str, lang: str) -> Optional[str]:
    """
    从文本中提取 ```lang ... ``` 代码块内容。
    如果找不到指定语言的块，返回第一个代码块内容。
    """
    pattern = re.compile(
        rf"```(?:{lang})?\s*\n?(.*?)\n?```",
        re.DOTALL | re.IGNORECASE,
    )
    matches = pattern.findall(text)
    if matches:
        return matches[0].strip()
    return None


def _parse_list_items(text: str) -> list[str]:
    """
    从 Markdown 列表文本中提取所有列表项。
    支持无序列表 (- item) 和有序列表 (1. item)。
    """
    items: list[str] = []

    for line in text.split("\n"):
        line = line.strip()
        # 无序列表
        m = re.match(r"^[-*+]\s+(.+)$", line)
        if m:
            items.append(m.group(1).strip())
            continue
        # 有序列表
        m = re.match(r"^\d+[.．)]\s+(.+)$", line)
        if m:
            items.append(m.group(1).strip())

    return items
