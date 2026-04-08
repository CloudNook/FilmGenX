"""
Gemini 图像批量生成测试。

功能：
- 并发调用 Gemini 文生图，支持批量多个提示词
- 生成结果保存到本地 ./output/ 目录

使用方式：
    cd backend
    .venv/bin/python tests/integration/test_gemini_image_batch.py
"""

from __future__ import annotations

import asyncio
import os
import sys
from datetime import datetime
from pathlib import Path

CURRENT_FILE = Path(__file__).resolve()
BACKEND_ROOT = CURRENT_FILE.parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.config import settings
from app.utils.image_gen import image_gen_client

# ============================================================
# 配置区 — 修改以下内容即可
# ============================================================

# 提示词数组，每个元素对应一次独立的图片生成任务
PROMPTS: list[str] = [
    "全景，云岚宗广场，宏伟石阶与大殿，众多弟子站立两侧围观，白底背景，3D真实动漫风格，高精度渲染，PBR材质，UE5风格",
    "中景，云岚宗中央比武台，圆形石台，周围站立数十名弟子，弟子穿统一白色长袍，表情期待，白底背景，3D真实动漫风格",
    "特写，云岚宗众弟子交头接耳，表情兴奋，手指前方，身穿统一白色云岚宗服饰，白底背景，3D真实动漫风格",
    "远景，云岚宗大殿前，宽阔广场，数百名弟子整齐列队，云雾缭绕山间，白底背景，3D真实动漫风格，高精度渲染"
]

# 生成参数
ASPECT_RATIO = "16:9"   # 支持: 1:1, 16:9, 9:16, 3:4, 4:3, 2:3, 3:2, 21:9 等
IMAGE_SIZE = "4K"        # 支持: 512, 1K, 2K, 4K

# 并发数量（同时发起的请求数）
CONCURRENCY = 4

# 输出目录
OUTPUT_DIR = Path(__file__).parent.parent.parent / "output"
# ============================================================


def _ensure_required_settings() -> None:
    if not settings.GOOGLE_API_KEY:
        raise RuntimeError("GOOGLE_API_KEY 未配置，请在 .env 中填写")


def _mime_to_extension(mime_type: str | None) -> str:
    if mime_type == "image/jpeg":
        return ".jpg"
    if mime_type == "image/webp":
        return ".webp"
    return ".png"


def _build_filename(prompt_index: int, mime_type: str | None) -> str:
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    return f"gemini_batch_{prompt_index:02d}_{timestamp}{_mime_to_extension(mime_type)}"


async def generate_single(prompt_index: int, prompt: str) -> tuple[int, str | None, str | None]:
    """执行单次图片生成并保存到本地。"""
    print(f"[{prompt_index}] 开始生成: {prompt[:40]}...")
    result = await image_gen_client.generate(
        prompt=prompt,
        aspect_ratio=ASPECT_RATIO,
        image_size=IMAGE_SIZE,
    )

    if not result.success or not result.image_data:
        print(f"[{prompt_index}] 失败: {result.error_message}")
        return prompt_index, None, result.error_message

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    filename = _build_filename(prompt_index, result.mime_type)
    filepath = OUTPUT_DIR / filename
    with open(filepath, "wb") as f:
        f.write(result.image_data)

    print(f"[{prompt_index}] 成功 -> {filepath}")
    return prompt_index, str(filepath), None


async def _main_async() -> int:
    _ensure_required_settings()

    if not PROMPTS:
        print("PROMPTS 数组为空，请在文件顶部添加提示词")
        return 1

    print(f"开始批量生成 {len(PROMPTS)} 张图片，并发数: {CONCURRENCY}")
    print(f"输出目录: {OUTPUT_DIR}\n")

    semaphore = asyncio.Semaphore(CONCURRENCY)

    async def bounded_generate(i: int, p: str):
        async with semaphore:
            return await generate_single(i, p)

    tasks = [bounded_generate(i, p) for i, p in enumerate(PROMPTS, start=1)]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    successes = 0
    failures = 0
    for r in results:
        if isinstance(r, Exception):
            failures += 1
            print(f"[ERROR] 异常: {r}")
        else:
            idx, path, err = r
            if path:
                successes += 1
            else:
                failures += 1

    print(f"\n完成！成功: {successes}  失败: {failures}")
    return 0


def main() -> int:
    return asyncio.run(_main_async())


if __name__ == "__main__":
    raise SystemExit(main())
