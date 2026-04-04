"""
Google Gemini 图像生成客户端。

使用 Gemini 3 Pro Image (gemini-3-pro-image-preview) 模型生成图像。

使用方式：
    from app.utils.image_gen import image_gen_client

    result = await image_gen_client.generate(
        prompt="一个穿着白袍的少年站在悬崖边",
        negative_prompt="模糊,低质量",
        aspect_ratio="16:9",
    )
    if result.image_data:
        # 保存图片
        with open("output.png", "wb") as f:
            f.write(result.image_data)
"""

import base64
import logging
from dataclasses import dataclass
from typing import Optional

from google import genai
from google.genai import types

from app.core.config import settings

logger = logging.getLogger(__name__)

# 允许的画幅比例
ASPECT_RATIOS = {
    "1:1": "1:1",
    "16:9": "16:9",
    "9:16": "9:16",
    "4:3": "4:3",
    "3:4": "3:4",
}

# 图像尺寸选项
IMAGE_SIZES = ["256", "512", "1024", "2K", "4K"]

# 默认模型
DEFAULT_MODEL = "gemini-3-pro-image-preview"


@dataclass
class ImageGenerationResult:
    """图像生成结果。"""

    success: bool
    image_data: Optional[bytes] = None  # PNG/JPEG 格式的二进制数据
    mime_type: Optional[str] = None  # image/png / image/jpeg
    rai_reason: Optional[str] = None  # Responsible AI 拒绝原因
    error_message: Optional[str] = None


class ImageGenClient:
    """Google Gemini 图像生成客户端。"""

    def __init__(self) -> None:
        self._client: Optional[genai.Client] = None

    def _get_client(self) -> genai.Client:
        """懒加载 Google Genai 客户端。"""
        if self._client is None:
            if not settings.GOOGLE_API_KEY:
                raise RuntimeError("GOOGLE_API_KEY 未配置，请在 .env 中填写")
            self._client = genai.Client(api_key=settings.GOOGLE_API_KEY)
        return self._client

    async def generate(
        self,
        *,
        prompt: str,
        negative_prompt: Optional[str] = None,
        aspect_ratio: str = "16:9",
        image_size: str = "1024",
        model: str = DEFAULT_MODEL,
    ) -> ImageGenerationResult:
        """生成图像。

        Args:
            prompt: 正向提示词，描述想要生成的画面。
            negative_prompt: 负向提示词（当前模型可能不支持）。
            aspect_ratio: 画幅比例，支持 1:1 / 16:9 / 9:16 / 4:3 / 3:4。
            image_size: 图像尺寸，支持 256 / 512 / 1024 / 2K / 4K。
            model: 使用的模型，默认 gemini-3-pro-image-preview。

        Returns:
            ImageGenerationResult，包含生成结果或错误信息。
        """
        import asyncio

        try:
            client = self._get_client()

            # 验证画幅比例
            if aspect_ratio not in ASPECT_RATIOS:
                logger.warning(f"不支持的画幅比例 '{aspect_ratio}'，使用默认 16:9")
                aspect_ratio = "16:9"

            # 验证图像尺寸
            if image_size not in IMAGE_SIZES:
                logger.warning(f"不支持的图像尺寸 '{image_size}'，使用默认 1024")
                image_size = "1024"

            # 构建完整提示词
            full_prompt = prompt
            if negative_prompt:
                # 注意：Gemini 可能不支持负向提示词，这里只是记录
                logger.info(f"负向提示词: {negative_prompt}")

            logger.info(
                f"Gemini Image 调用: model={model}, prompt={prompt[:50]}..., "
                f"aspect_ratio={aspect_ratio}, image_size={image_size}"
            )

            def _sync_generate():
                return client.models.generate_content(
                    model=model,
                    contents=full_prompt,
                    config=types.GenerateContentConfig(
                        response_modalities=["IMAGE"],
                        image_config=types.ImageConfig(
                            aspect_ratio=aspect_ratio,
                            image_size=image_size,
                        ),
                    ),
                )

            # 在线程池中运行同步调用
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(None, _sync_generate)

            # 处理响应，提取图片数据
            image_data = None
            mime_type = "image/png"

            for part in response.candidates[0].content.parts:
                if part.inline_data:
                    image_data = base64.b64decode(part.inline_data.data)
                    mime_type = part.inline_data.mime_type or "image/png"
                    logger.info(f"获取到图片: mime_type={mime_type}, size={len(image_data)} bytes")
                    break

            if not image_data:
                # 检查是否有文本响应（可能是 RAI 拒绝）
                text_response = response.text if hasattr(response, "text") else None
                if text_response:
                    return ImageGenerationResult(
                        success=False,
                        error_message=f"模型返回文本而非图片: {text_response[:200]}",
                    )
                return ImageGenerationResult(
                    success=False,
                    error_message="未生成任何图片数据",
                )

            logger.info(f"Gemini Image 生成成功: size={len(image_data)} bytes")

            return ImageGenerationResult(
                success=True,
                image_data=image_data,
                mime_type=mime_type,
            )

        except Exception as e:
            error_msg = str(e)
            logger.error(f"Gemini Image 生成失败: {error_msg}")
            return ImageGenerationResult(
                success=False,
                error_message=error_msg,
            )


# 全局单例
image_gen_client = ImageGenClient()
