"""
Skill 引用 token 解析与 lint。

@ 引用语法（在 body 或 reference body 内书写）：
- ``@ref:<key>``             — 当前 skill 的某个 reference
- ``@skill:<name>``          — 跨 skill 整体（LLM 决策是否 load_skill）
- ``@skill:<name>#<key>``    — 跨 skill 的某个 reference

DB 里始终存原始 token 字符串，不做转义；前端预览时再叠加样式。

设计要点：
- 解析器纯函数：``parse_reference_tokens(text) -> list[Token]``
- Lint 在保存前跑，issue 列表返给 admin（不阻断保存，警告而已）
- 不在框架运行时强制：跨 skill 引用最终是否 fetch 由 LLM 决定，框架只校验语法和指向有效性
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Iterable, Literal, Optional


# 顺序很重要：先匹配 @skill:<name>#<key>，再 @skill:<name>，最后 @ref:<key>
# 否则 ``@skill:foo#bar`` 会被 ``@skill:foo`` 截断
TOKEN_PATTERN = re.compile(
    r"@(?:"
    r"skill:(?P<skill_with_ref>[a-z0-9][a-z0-9_-]*)"
    r"#(?P<skill_ref_key>[a-z0-9][a-z0-9_-]*)"
    r"|"
    r"skill:(?P<skill_only>[a-z0-9][a-z0-9_-]*)"
    r"|"
    r"ref:(?P<self_ref_key>[a-z0-9][a-z0-9_-]*)"
    r")"
)


TokenKind = Literal["self_ref", "skill", "skill_ref"]


@dataclass(frozen=True)
class SkillReferenceToken:
    """一个 @ 引用 token 的解析结果。"""

    kind: TokenKind
    raw: str
    skill_name: Optional[str] = None  # kind != "self_ref" 时填写
    ref_key: Optional[str] = None  # kind != "skill" 时填写
    span: Optional[tuple[int, int]] = None  # 在源文本中的偏移（用于前端高亮）


def parse_reference_tokens(text: Optional[str]) -> list[SkillReferenceToken]:
    """从一段 markdown 中解析所有 @ 引用 token。"""
    if not text:
        return []
    tokens: list[SkillReferenceToken] = []
    for match in TOKEN_PATTERN.finditer(text):
        if match.group("skill_with_ref") is not None:
            tokens.append(
                SkillReferenceToken(
                    kind="skill_ref",
                    raw=match.group(0),
                    skill_name=match.group("skill_with_ref"),
                    ref_key=match.group("skill_ref_key"),
                    span=match.span(),
                )
            )
        elif match.group("skill_only") is not None:
            tokens.append(
                SkillReferenceToken(
                    kind="skill",
                    raw=match.group(0),
                    skill_name=match.group("skill_only"),
                    span=match.span(),
                )
            )
        elif match.group("self_ref_key") is not None:
            tokens.append(
                SkillReferenceToken(
                    kind="self_ref",
                    raw=match.group(0),
                    ref_key=match.group("self_ref_key"),
                    span=match.span(),
                )
            )
    return tokens


# ---------------------------------------------------------------------- #
# Lint
# ---------------------------------------------------------------------- #


LintLevel = Literal["error", "warning"]
LintCode = Literal[
    "DEAD_REF",
    "ORPHAN_REF",
    "UNKNOWN_SKILL",
    "UNKNOWN_SKILL_REF",
    "INACTIVE_SKILL",
    "DUPLICATE_REF_KEY",
]


@dataclass
class LintIssue:
    level: LintLevel
    code: LintCode
    message: str
    field: str
    token: Optional[str] = None


@dataclass(frozen=True)
class SkillLikeView:
    """lint 需要的最小投影：解耦 ORM 类型，方便测试和服务层调用。"""

    name: str
    is_active: bool
    body: Optional[str]
    references: list[dict] = field(default_factory=list)

    @property
    def reference_keys(self) -> set[str]:
        return {r["key"] for r in self.references if isinstance(r, dict) and r.get("key")}


def lint_skill(
    target: SkillLikeView,
    *,
    all_skills_by_name: dict[str, SkillLikeView],
) -> list[LintIssue]:
    """对一个 skill 跑 lint，返回 issue 列表（不阻断保存）。

    检查项：
    - DEAD_REF: ``@ref:foo`` 但 references 中无 key=foo
    - ORPHAN_REF: references 里定义了 key=foo 但 body / 任何 reference body 都没有 ``@ref:foo``
    - UNKNOWN_SKILL: ``@skill:foo`` 指向不存在的 skill
    - INACTIVE_SKILL: ``@skill:foo`` 指向 is_active=False
    - UNKNOWN_SKILL_REF: ``@skill:foo#bar`` 但 foo.references 中没有 key=bar
    - DUPLICATE_REF_KEY: references 里同 key 出现多次
    """
    issues: list[LintIssue] = []

    # 1. references 自身的去重检查
    seen_keys: set[str] = set()
    for ref in target.references or []:
        key = ref.get("key") if isinstance(ref, dict) else None
        if not key:
            continue
        if key in seen_keys:
            issues.append(
                LintIssue(
                    level="warning",
                    code="DUPLICATE_REF_KEY",
                    message=f"reference key '{key}' 重复，后者会覆盖前者",
                    field=f"references[{key}]",
                )
            )
        seen_keys.add(key)

    own_keys = target.reference_keys

    # 2. 收集所有 @ 引用 token：body + 每个 reference body 都要扫
    body_tokens = parse_reference_tokens(target.body)
    ref_tokens: dict[str, list[SkillReferenceToken]] = {}
    for ref in target.references or []:
        if not isinstance(ref, dict):
            continue
        key = ref.get("key")
        if not key:
            continue
        ref_tokens[key] = parse_reference_tokens(ref.get("body"))

    # 3. 校验 self_ref 指向有效（DEAD_REF）
    self_ref_keys_used: set[str] = set()
    for token in body_tokens:
        if token.kind == "self_ref":
            self_ref_keys_used.add(token.ref_key or "")
            if token.ref_key not in own_keys:
                issues.append(
                    LintIssue(
                        level="error",
                        code="DEAD_REF",
                        message=f"body 引用了不存在的 reference key: {token.ref_key!r}",
                        field="body",
                        token=token.raw,
                    )
                )
    for ref_key, tokens in ref_tokens.items():
        for token in tokens:
            if token.kind == "self_ref":
                self_ref_keys_used.add(token.ref_key or "")
                if token.ref_key not in own_keys:
                    issues.append(
                        LintIssue(
                            level="error",
                            code="DEAD_REF",
                            message=(
                                f"references[{ref_key}] 引用了不存在的 reference key: "
                                f"{token.ref_key!r}"
                            ),
                            field=f"references[{ref_key}]",
                            token=token.raw,
                        )
                    )

    # 4. 孤立 reference（ORPHAN_REF）：定义了但没人 @ref 它
    for key in own_keys:
        if key not in self_ref_keys_used:
            issues.append(
                LintIssue(
                    level="warning",
                    code="ORPHAN_REF",
                    message=(
                        f"references[{key}] 在 body / 其它 reference 内未被 @ref:{key} 引用，"
                        "LLM 不会有线索去加载它"
                    ),
                    field=f"references[{key}]",
                )
            )

    # 5. 跨 skill 引用：UNKNOWN_SKILL / UNKNOWN_SKILL_REF / INACTIVE_SKILL
    cross_tokens: Iterable[tuple[str, SkillReferenceToken]] = (
        [("body", t) for t in body_tokens]
        + [
            (f"references[{ref_key}]", t)
            for ref_key, tokens in ref_tokens.items()
            for t in tokens
        ]
    )
    for source_field, token in cross_tokens:
        if token.kind not in ("skill", "skill_ref"):
            continue
        if token.skill_name == target.name:
            # 指向自己的 skill：建议改写为 @ref，但不报 lint，由人决定
            continue
        target_skill = all_skills_by_name.get(token.skill_name or "")
        if target_skill is None:
            issues.append(
                LintIssue(
                    level="error",
                    code="UNKNOWN_SKILL",
                    message=f"@skill:{token.skill_name} 指向的 skill 不存在",
                    field=source_field,
                    token=token.raw,
                )
            )
            continue
        if not target_skill.is_active:
            issues.append(
                LintIssue(
                    level="warning",
                    code="INACTIVE_SKILL",
                    message=f"@skill:{token.skill_name} 指向的 skill 已禁用",
                    field=source_field,
                    token=token.raw,
                )
            )
        if token.kind == "skill_ref":
            if token.ref_key not in target_skill.reference_keys:
                issues.append(
                    LintIssue(
                        level="error",
                        code="UNKNOWN_SKILL_REF",
                        message=(
                            f"@skill:{token.skill_name}#{token.ref_key} 指向的 reference "
                            "不存在"
                        ),
                        field=source_field,
                        token=token.raw,
                    )
                )

    return issues
