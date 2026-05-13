"""
Seed skill library from frontend/lib/skill-samples.ts.

把前端 SKILL_SAMPLES 里全部 skill 模板直接灌进 DB，避免一个一个去 admin 页面手动
应用。所有 skill 走 upsert——已存在的更新，不存在的新建。

运行方式：
    cd backend
    python scripts/seed_skills.py                # 全部 seed
    python scripts/seed_skills.py --dry-run      # 只解析、不写 DB
    python scripts/seed_skills.py --only NAME    # 只 seed 指定 skill（可多次传）
"""

from __future__ import annotations

import argparse
import asyncio
import re
import sys
from pathlib import Path

# 让 `python scripts/seed_skills.py` 能找到 app 包
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db.session import AsyncSessionFactory  # noqa: E402
from app.schemas.skill import SkillCreate, SkillReferenceItem  # noqa: E402
from app.services.skill_parser import parse_skill_markdown  # noqa: E402
from app.services.skill_service import SkillService  # noqa: E402


# 前端模板源文件路径（相对仓库根）
SKILL_SAMPLES_PATH = (
    Path(__file__).resolve().parents[2]
    / "frontend"
    / "lib"
    / "skill-samples.ts"
)

# 匹配 `const XXX = \`...\`;`（multiline）
# `[\s\S]*?` 非贪婪跨行；结尾必须是单独一行 \`;
CONST_BLOCK_RE = re.compile(
    r"^const\s+([A-Z][A-Z0-9_]*)\s*=\s*`([\s\S]*?)`;\s*$",
    re.MULTILINE,
)


def _unescape_ts_template(s: str) -> str:
    """把 TS template literal 内部的 \\` 还原成裸 `。"""
    return s.replace("\\`", "`")


def extract_skill_markdowns() -> list[tuple[str, str]]:
    """从 skill-samples.ts 提取所有 const 的 markdown 内容。

    Returns:
        list of (const_name, raw_markdown)。const_name 是 TS 中的常量名
        （如 ``CHARACTER_DESIGN``），raw_markdown 是 frontmatter + body 全文。
    """
    if not SKILL_SAMPLES_PATH.exists():
        raise FileNotFoundError(f"找不到 {SKILL_SAMPLES_PATH}")

    source = SKILL_SAMPLES_PATH.read_text(encoding="utf-8")
    results: list[tuple[str, str]] = []
    for match in CONST_BLOCK_RE.finditer(source):
        const_name = match.group(1)
        raw_markdown = _unescape_ts_template(match.group(2))
        # 只挑 frontmatter 起手的（避免误命中其他常量）
        if raw_markdown.lstrip().startswith("---"):
            results.append((const_name, raw_markdown))
    return results


def parse_markdown_to_create(raw_markdown: str) -> tuple[SkillCreate, list[str]]:
    """解析 markdown → SkillCreate。

    Returns:
        (SkillCreate, warnings)。warnings 包含 parser 产生的告警信息。
    """
    parse_result = parse_skill_markdown(raw_markdown)
    fields = parse_result.fields

    if parse_result.missing_fields:
        raise ValueError(
            f"必填字段缺失: {parse_result.missing_fields}（name={fields.get('name')!r}）"
        )

    refs_raw = fields.get("references") or []
    references: list[SkillReferenceItem] = []
    for ref in refs_raw:
        if isinstance(ref, dict):
            references.append(SkillReferenceItem(**ref))
        elif isinstance(ref, SkillReferenceItem):
            references.append(ref)
        else:
            raise ValueError(f"意外的 reference 形态: {type(ref)}")

    create = SkillCreate(
        name=fields["name"],
        description=fields["description"],
        target_agents=fields.get("target_agents") or [],
        body=fields.get("body") or None,
        references=references,
        tags=fields.get("tags") or [],
        author=fields.get("author") or None,
        raw_markdown=raw_markdown,
        is_active=True,
        metadata=fields.get("metadata") or {},
    )

    warnings = [f"{w.field}: {w.message}" for w in parse_result.warnings]
    return create, warnings


async def seed_one(
    service: SkillService,
    create: SkillCreate,
    raw_markdown: str,
) -> tuple[str, bool]:
    """upsert 单个 skill。

    Returns:
        (skill.name, is_update)
    """
    existing = await service.repo.get_by_name(create.name)
    is_update = existing is not None
    await service.save_skill(create, raw_markdown=raw_markdown)
    return create.name, is_update


async def main(only: set[str] | None, dry_run: bool) -> int:
    print(f"📄 读取 {SKILL_SAMPLES_PATH}")
    blocks = extract_skill_markdowns()
    print(f"   找到 {len(blocks)} 个 skill 块\n")

    parsed: list[tuple[str, SkillCreate, str, list[str]]] = []
    for const_name, raw in blocks:
        try:
            create, warnings = parse_markdown_to_create(raw)
        except Exception as exc:  # noqa: BLE001
            print(f"❌ [{const_name}] 解析失败: {exc}")
            return 1
        parsed.append((const_name, create, raw, warnings))

    # filter
    if only:
        before = len(parsed)
        parsed = [p for p in parsed if p[1].name in only]
        print(
            f"🔎 --only 过滤: {before} → {len(parsed)} "
            f"（命中: {sorted(p[1].name for p in parsed)}）\n"
        )
        if not parsed:
            print("⚠️  没有匹配的 skill；可用的 name 为：")
            for const_name, _create, _raw, _w in (
                (n, c, r, w)
                for (n, c, r, w) in [
                    (cn, *parse_markdown_to_create(rw), rw)  # noqa
                    for cn, rw in blocks
                ]
            ):
                pass
            return 1

    print("📋 即将 seed 的 skill：")
    for const_name, create, _raw, warnings in parsed:
        flag_warn = f"  ⚠️  {len(warnings)} warnings" if warnings else ""
        agents = ", ".join(create.target_agents) or "(none)"
        print(
            f"   - {create.name:36s}  ←  {const_name}  "
            f"[target: {agents}]{flag_warn}"
        )
        for w in warnings:
            print(f"      ⚠️  {w}")
    print()

    if dry_run:
        print("✅ Dry run 完成，未写 DB。")
        return 0

    created = 0
    updated = 0
    async with AsyncSessionFactory() as db:
        service = SkillService(db)
        for _const_name, create, raw, _warnings in parsed:
            try:
                name, is_update = await seed_one(service, create, raw)
            except Exception as exc:  # noqa: BLE001
                print(f"❌ [{create.name}] 保存失败: {exc}")
                return 1
            if is_update:
                updated += 1
                print(f"   🔄 updated  {name}")
            else:
                created += 1
                print(f"   ✨ created  {name}")

    print(
        f"\n✅ 完成：{created} 新建 / {updated} 更新（共 {created + updated} 条）"
    )
    return 0


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="把 frontend/lib/skill-samples.ts 里全部 skill 灌进 DB。",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="只解析、不写 DB",
    )
    parser.add_argument(
        "--only",
        action="append",
        metavar="NAME",
        help="只 seed 指定 skill name（可多次传），例如 --only character-design",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    only = set(args.only) if args.only else None
    sys.exit(asyncio.run(main(only=only, dry_run=args.dry_run)))
