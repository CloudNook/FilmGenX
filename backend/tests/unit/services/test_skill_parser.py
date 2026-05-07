"""
SKILL.md 解析器（Claude 风格）单元测试。

覆盖：
- frontmatter 提取（name / description / target_agents / tags / author / metadata）
- body 与 references 分离（## reference: <key>）
- 旧格式兼容：检测 ## content / ## examples / ## constraints / ## parameters 给 warning
- 缺字段、非法 reference key、重复 key 的容错
"""

from app.services.skill_parser import parse_skill_markdown


def test_parses_full_skill_md():
    md = """---
name: narrative-structure
description: Use when designing story outlines.
target_agents: [outline_agent]
tags: [storytelling, structure]
author: amanda
---

# 三幕结构

主体内容。看 @ref:act-templates 拿模板。

## reference: act-templates

模板内容...

## reference: pacing-checklist

清单内容...
"""
    r = parse_skill_markdown(md)
    assert r.missing_fields == []
    assert r.fields["name"] == "narrative-structure"
    assert r.fields["description"].startswith("Use when")
    assert r.fields["target_agents"] == ["outline_agent"]
    assert r.fields["tags"] == ["storytelling", "structure"]
    assert r.fields["author"] == "amanda"
    body = r.fields["body"]
    assert "三幕结构" in body
    assert "## reference:" not in body, "reference 段应被剥离出 body"
    refs = r.fields["references"]
    assert {x["key"] for x in refs} == {"act-templates", "pacing-checklist"}
    assert refs[0]["title"] == "Act Templates"
    assert "模板内容" in refs[0]["body"]


def test_legacy_section_warns_but_keeps_body():
    md = """---
name: legacy
description: legacy format
---

主体...

## content

旧的 content 段。

## examples

- 示例 1
- 示例 2
"""
    r = parse_skill_markdown(md)
    # 不再单独提取 examples / content；它们整体留在 body 里
    assert "## content" in r.fields["body"]
    assert "## examples" in r.fields["body"]
    # 给 admin 一个迁移提示
    legacy_warns = [w for w in r.warnings if "遗留 section" in w.message]
    assert len(legacy_warns) == 1


def test_missing_required_fields():
    r = parse_skill_markdown("")
    assert "name" in r.missing_fields
    assert "description" in r.missing_fields


def test_target_agents_string_form():
    md = """---
name: x
description: y
target_agents: outline_agent, script_agent
---

body
"""
    r = parse_skill_markdown(md)
    assert r.fields["target_agents"] == ["outline_agent", "script_agent"]


def test_invalid_reference_key_skipped_with_warning():
    md = """---
name: x
description: y
---

## reference: BadKey!

body of ref
"""
    r = parse_skill_markdown(md)
    assert r.fields["references"] == []
    assert any(w.field == "references" for w in r.warnings)


def test_duplicate_reference_key_kept_last():
    md = """---
name: x
description: y
---

## reference: foo

first

## reference: foo

second
"""
    r = parse_skill_markdown(md)
    refs = r.fields["references"]
    assert len(refs) == 1
    assert refs[0]["body"].strip() == "second"
    assert any("重复" in w.message for w in r.warnings)


def test_no_frontmatter_still_parses_body_and_records_missing():
    md = """没有 frontmatter 的 markdown.

## reference: hint

ref body.
"""
    r = parse_skill_markdown(md)
    assert "name" in r.missing_fields
    assert "description" in r.missing_fields
    refs = r.fields.get("references", [])
    assert refs and refs[0]["key"] == "hint"


def test_frontmatter_yaml_error_warns_and_continues():
    md = """---
name: bad
description: : : :
target_agents: [unclosed
---

body
"""
    r = parse_skill_markdown(md)
    # 至少给出 frontmatter warning
    assert any(w.field == "frontmatter" for w in r.warnings)
