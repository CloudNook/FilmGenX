"""
@ 引用 token 解析 + lint 单元测试。
"""

from app.services.skill_references import (
    SkillLikeView,
    lint_skill,
    parse_reference_tokens,
)


# ---------------------------------------------------------------------- #
# parse_reference_tokens
# ---------------------------------------------------------------------- #


def test_parses_self_ref_token():
    tokens = parse_reference_tokens("look at @ref:act-templates please")
    assert len(tokens) == 1
    t = tokens[0]
    assert t.kind == "self_ref"
    assert t.ref_key == "act-templates"
    assert t.skill_name is None
    assert t.raw == "@ref:act-templates"


def test_parses_skill_only_token():
    tokens = parse_reference_tokens("see @skill:character-arc")
    assert len(tokens) == 1
    t = tokens[0]
    assert t.kind == "skill"
    assert t.skill_name == "character-arc"
    assert t.ref_key is None


def test_parses_skill_ref_token():
    tokens = parse_reference_tokens("see @skill:character-arc#wants-needs section")
    assert len(tokens) == 1
    t = tokens[0]
    assert t.kind == "skill_ref"
    assert t.skill_name == "character-arc"
    assert t.ref_key == "wants-needs"


def test_parses_multiple_tokens_in_order():
    text = "@ref:a then @skill:b#c then @skill:d alone"
    tokens = parse_reference_tokens(text)
    kinds = [t.kind for t in tokens]
    assert kinds == ["self_ref", "skill_ref", "skill"]


def test_handles_none_or_empty():
    assert parse_reference_tokens(None) == []
    assert parse_reference_tokens("") == []


# ---------------------------------------------------------------------- #
# lint_skill
# ---------------------------------------------------------------------- #


def _view(name, *, body="", references=None, is_active=True):
    return SkillLikeView(
        name=name,
        is_active=is_active,
        body=body,
        references=references or [],
    )


def test_lint_dead_ref_in_body():
    me = _view(
        "x",
        body="see @ref:nope",
        references=[{"key": "real", "body": ""}],
    )
    issues = lint_skill(me, all_skills_by_name={"x": me})
    codes = [i.code for i in issues]
    assert "DEAD_REF" in codes


def test_lint_orphan_ref():
    me = _view(
        "x",
        body="just plain text",
        references=[{"key": "lonely", "body": ""}],
    )
    issues = lint_skill(me, all_skills_by_name={"x": me})
    orphan = [i for i in issues if i.code == "ORPHAN_REF"]
    assert len(orphan) == 1
    assert orphan[0].field == "references[lonely]"


def test_lint_unknown_skill():
    me = _view("x", body="@skill:nonexistent")
    issues = lint_skill(me, all_skills_by_name={"x": me})
    codes = [i.code for i in issues]
    assert "UNKNOWN_SKILL" in codes


def test_lint_inactive_skill_warning():
    me = _view("x", body="@skill:disabled")
    target = _view("disabled", is_active=False)
    issues = lint_skill(me, all_skills_by_name={"x": me, "disabled": target})
    codes = [i.code for i in issues]
    assert "INACTIVE_SKILL" in codes


def test_lint_unknown_skill_ref():
    me = _view("x", body="@skill:other#missing")
    other = _view(
        "other",
        body="",
        references=[{"key": "exists", "body": ""}],
    )
    issues = lint_skill(me, all_skills_by_name={"x": me, "other": other})
    codes = [i.code for i in issues]
    assert "UNKNOWN_SKILL_REF" in codes


def test_lint_clean_when_everything_resolves():
    me = _view(
        "x",
        body="see @ref:a and @skill:y#b",
        references=[{"key": "a", "body": ""}],
    )
    other = _view(
        "y",
        body="",
        references=[{"key": "b", "body": ""}],
    )
    issues = lint_skill(me, all_skills_by_name={"x": me, "y": other})
    assert issues == []


def test_lint_self_ref_inside_reference_body_also_checked():
    """references[r1].body 里的 @ref:nope 也要被 lint 抓到。"""
    me = _view(
        "x",
        body="@ref:r1",
        references=[
            {"key": "r1", "body": "depends on @ref:nope"},
        ],
    )
    issues = lint_skill(me, all_skills_by_name={"x": me})
    dead = [i for i in issues if i.code == "DEAD_REF"]
    assert any(i.field == "references[r1]" for i in dead)


def test_lint_duplicate_ref_key():
    me = _view(
        "x",
        body="@ref:r1",
        references=[
            {"key": "r1", "body": "v1"},
            {"key": "r1", "body": "v2"},
        ],
    )
    issues = lint_skill(me, all_skills_by_name={"x": me})
    codes = [i.code for i in issues]
    assert "DUPLICATE_REF_KEY" in codes
