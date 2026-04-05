"""
Gemini 图像生成集成测试。

功能：
1. 文生图：调用 Gemini 生成图片并上传到 OSS/CDN。
2. 图生图：下载给定的 CDN 图片作为参考图，结合提示词生成新图并上传到 OSS/CDN。

调试方式：
1. 直接修改本文件顶部的提示词和 CDN 数组。
2. 在 main() 里注释掉不想运行的函数。
3. 执行：
    cd backend
    .venv/bin/python tests/integration/test_gemini_image_cdn.py
"""

from __future__ import annotations

import asyncio
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

import httpx


CURRENT_FILE = Path(__file__).resolve()
BACKEND_ROOT = CURRENT_FILE.parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.config import settings
from app.utils.image_gen import image_gen_client
from app.utils.oss import oss_client


TEXT_TO_IMAGE_PROMPT = """
萧炎，20岁东方男性，黑发束起，金色瞳孔，下颌线锋利，面容冷峻。身穿深色战袍，布料厚重有磨损焦痕，背后斜背黑色玄重尺。厚涂动漫风格，电影级光影，暗部冷紫，高光青白。4K，16:9，超高细节，非平涂卡通。全身站立正面照，干净背景。
"""
IMAGE_TO_IMAGE_PROMPT = "帮我扩展成真实动漫全景3d图，保持人物主体不变，扩充周围场景，增加更多细节和环境元素，保持原图风格一致。"
NEGATIVE_PROMPT: Optional[str] = None
ASPECT_RATIO = "16:9"
IMAGE_SIZE = "1K"
OSS_DIRECTORY = "tests/gemini"

# 把你的 CDN 图片链接填在这里。图生图默认使用第一张。
REFERENCE_CDN_URLS: list[str] = [
     "https://film-gen-x-dev.oss-cn-hangzhou.aliyuncs.com/filmgenx/dev/tests/gemini/gemini_img2img_20260405032659.jpg",
]


def _ensure_required_settings() -> None:
    missing = []
    if not settings.GOOGLE_API_KEY:
        missing.append("GOOGLE_API_KEY")
    if not settings.OSS_ACCESS_KEY_ID:
        missing.append("OSS_ACCESS_KEY_ID")
    if not settings.OSS_ACCESS_KEY_SECRET:
        missing.append("OSS_ACCESS_KEY_SECRET")
    if not settings.OSS_BUCKET_NAME:
        missing.append("OSS_BUCKET_NAME")
    if not settings.OSS_ENDPOINT:
        missing.append("OSS_ENDPOINT")

    if missing:
        raise RuntimeError(f"缺少必要配置: {', '.join(missing)}")


def _mime_to_extension(mime_type: Optional[str]) -> str:
    if mime_type == "image/jpeg":
        return ".jpg"
    if mime_type == "image/webp":
        return ".webp"
    return ".png"


def _build_filename(prefix: str, mime_type: Optional[str]) -> str:
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    return f"{prefix}_{timestamp}{_mime_to_extension(mime_type)}"


async def _download_reference_image(url: str) -> bytes:
    async with httpx.AsyncClient(timeout=60, trust_env=settings.HTTP_TRUST_ENV) as client:
        response = await client.get(url)
        response.raise_for_status()
        return response.content


async def run_text_to_image(
) -> str:
    result = await image_gen_client.generate(
        prompt=TEXT_TO_IMAGE_PROMPT,
        negative_prompt=NEGATIVE_PROMPT,
        aspect_ratio=ASPECT_RATIO,
        image_size=IMAGE_SIZE,
    )
    if not result.success or not result.image_data:
        raise RuntimeError(result.error_message or "Gemini 文生图失败")

    cdn_url = oss_client.upload_bytes(
        result.image_data,
        filename=_build_filename("gemini_text2img", result.mime_type),
        directory=OSS_DIRECTORY,
        unique=False,
    )
    print(f"[text2img] CDN URL: {cdn_url}")
    return cdn_url


async def run_image_to_image(
) -> str:
    if not REFERENCE_CDN_URLS:
        raise ValueError("REFERENCE_CDN_URLS 为空，请先在文件顶部填入至少一个 CDN 链接")

    reference_url = REFERENCE_CDN_URLS[0]
    reference_image = await _download_reference_image(reference_url)
    result = await image_gen_client.generate_with_reference(
        prompt=IMAGE_TO_IMAGE_PROMPT,
        reference_images=[reference_image],
        negative_prompt=NEGATIVE_PROMPT,
        aspect_ratio=ASPECT_RATIO,
        image_size=IMAGE_SIZE,
    )
    if not result.success or not result.image_data:
        raise RuntimeError(result.error_message or "Gemini 图生图失败")

    cdn_url = oss_client.upload_bytes(
        result.image_data,
        filename=_build_filename("gemini_img2img", result.mime_type),
        directory=OSS_DIRECTORY,
        unique=False,
    )
    print(f"[img2img] CDN URL: {cdn_url}")
    return cdn_url


async def _main_async() -> int:
    _ensure_required_settings()

    # await run_text_to_image()
    await run_image_to_image()

    return 0


def main() -> int:
    return asyncio.run(_main_async())


if __name__ == "__main__":
    raise SystemExit(main())
