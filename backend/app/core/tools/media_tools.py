"""
图像 / 视频生成工具（框架层薄包装）。

设计原则：
- 工具表面只暴露 ``generate_image`` / ``generate_video`` 两个名字
- 模型选择走 **参数**（带默认值）；后续新增模型 / provider 不要拆新工具，扩 model 字面量 + utils 加 adapter 即可
- 任何业务概念（asset / 角色锚 / 镜头号）都不出现在这里——本期 generate_* 只接受文字 prompt，
  参考图 / asset_code 等待 project-level memory 落地后再加入参（见 docs/engineering/TODO.md）
- 失败走 ``tool_error()`` 返回结构化对象，LLM 自己读 message / hint 决策

工具一览：
- ``generate_image(prompt, ..., model=...)``
    支持 ``model="gemini-3-pro-image-preview"`` (默认) / ``"gemini-3.1-flash-image-preview"``
- ``generate_video(prompt, ..., model=...)``
    支持 ``model="kling"`` (默认)；``"seedance"`` 已留接入位但当前返回 MODEL_NOT_AVAILABLE
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from app.core.agent.tool_errors import tool_error
from app.core.tools.registry import register_tool

logger = logging.getLogger(__name__)


_DEFAULT_IMAGE_DIR = "supervisor/images"
_DEFAULT_VIDEO_DIR = "supervisor/videos"

# video_prompt schema 的 quality 是 std/hq；evolink 那边是 720p/1080p
_VIDEO_QUALITY_MAP = {"std": "720p", "hq": "1080p"}

# 受支持的图像模型（其它值会落 IMAGE_MODEL_NOT_AVAILABLE）
_SUPPORTED_IMAGE_MODELS = {
    "gemini-3-pro-image-preview",
    "gemini-3.1-flash-image-preview",
}

# 受支持的视频模型——seedance 已声明但 utils 未真接入；调到时返回结构化错误
_SUPPORTED_VIDEO_MODELS = {"kling", "seedance"}


@register_tool(
    name="generate_image",
    description=(
        "文字驱动图像生成。模型由参数选择，产物自动落 OSS 返回永久 URL。\n"
        "Args:\n"
        "  prompt: 中文图像提示词（构图 + 角色 + 场景 + 光影 + 道具）\n"
        "  negative_prompt: 负面提示词（可选）\n"
        "  aspect_ratio: '16:9' / '9:16' / '1:1' / '3:4' / '4:3'，默认 '16:9'\n"
        "  image_size: '512' / '1K' / '2K' / '4K'，默认 '1K'\n"
        "  model: 'gemini-3-pro-image-preview'（默认，关键首帧 / 慢但好）\n"
        "         或 'gemini-3.1-flash-image-preview'（草图 / 快速预览）\n"
        "  oss_directory: OSS 目录，默认 'supervisor/images'\n"
        "Returns:\n"
        "  {success: True, url, model, mime_type, ...}；失败返回 tool_error 结构。\n"
        "本期暂不支持参考图入参，等 project-level memory 落地后会加 reference_assets。"
    ),
)
async def generate_image(
    prompt: str,
    negative_prompt: Optional[str] = None,
    aspect_ratio: str = "16:9",
    image_size: str = "1K",
    model: str = "gemini-3-pro-image-preview",
    oss_directory: str = _DEFAULT_IMAGE_DIR,
) -> Dict[str, Any]:
    if model not in _SUPPORTED_IMAGE_MODELS:
        return tool_error(
            error_code="IMAGE_MODEL_NOT_AVAILABLE",
            message=f"图像模型 {model!r} 暂不支持",
            hint=(
                "可选值：'gemini-3-pro-image-preview' (默认) "
                "/ 'gemini-3.1-flash-image-preview'"
            ),
            context={"requested_model": model},
        )

    from app.utils.image_gen import image_gen_client
    from app.utils.oss import oss_client

    try:
        result = await image_gen_client.generate(
            prompt=prompt,
            negative_prompt=negative_prompt,
            aspect_ratio=aspect_ratio,
            image_size=image_size,
            model=model,
        )
    except Exception as exc:
        logger.exception("[media_tools] image_gen 调用异常 model=%s", model)
        return tool_error(
            error_code="IMAGE_GEN_EXCEPTION",
            message=f"图像生成调用异常：{exc}",
            hint="检查 GOOGLE_API_KEY 配置或重试；持续失败可换 flash 模型",
            context={"model": model},
        )

    if not result.success or not result.image_data:
        return tool_error(
            error_code="IMAGE_GEN_FAILED",
            message=result.error_message or "图像生成失败但模型未返回原因",
            hint="尝试调整 prompt（更具体 / 移除敏感词）后重试",
            context={"model": model, "rai_reason": result.rai_reason},
        )

    suffix = "png" if (result.mime_type or "").endswith("png") else "jpg"
    try:
        url = oss_client.upload_bytes(
            result.image_data,
            filename=f"frame.{suffix}",
            directory=oss_directory,
        )
    except Exception as exc:
        logger.exception("[media_tools] OSS 上传异常")
        return tool_error(
            error_code="OSS_UPLOAD_FAILED",
            message=f"图像生成成功但落 OSS 失败：{exc}",
            hint="稍后重试；这是基础设施异常不应自我纠正",
            context={"model": model},
        )

    return {
        "success": True,
        "url": url,
        "model": model,
        "mime_type": result.mime_type,
        "aspect_ratio": aspect_ratio,
        "image_size": image_size,
    }


@register_tool(
    name="generate_video",
    description=(
        "文字驱动视频生成。模型由参数选择，产物自动落 OSS 返回永久 URL。\n"
        "Args:\n"
        "  prompt: 中文运动 prompt（运镜 + 角色动作 + 节奏）\n"
        "  duration: 时长秒，3-15，默认 5\n"
        "  aspect_ratio: '16:9' / '9:16' / '1:1'，默认 '16:9'\n"
        "  quality: 'std' (720p) / 'hq' (1080p)，默认 'std'\n"
        "  model: 'kling'（默认，已就绪）；'seedance'（占位，调用会返回 MODEL_NOT_AVAILABLE）\n"
        "  oss_directory: OSS 目录，默认 'supervisor/videos'\n"
        "Returns:\n"
        "  {success: True, url, task_id, model, duration, ...}；失败返回 tool_error 结构。\n"
        "本期不接受 image_start / end_frame 等参考图入参；等 memory 落地后会加。"
    ),
)
async def generate_video(
    prompt: str,
    duration: int = 5,
    aspect_ratio: str = "16:9",
    quality: str = "std",
    model: str = "kling",
    oss_directory: str = _DEFAULT_VIDEO_DIR,
) -> Dict[str, Any]:
    if model not in _SUPPORTED_VIDEO_MODELS:
        return tool_error(
            error_code="VIDEO_MODEL_NOT_AVAILABLE",
            message=f"视频模型 {model!r} 暂不支持",
            hint="可选值：'kling' (默认)；'seedance' 后续接入",
            context={"requested_model": model},
        )

    if model == "seedance":
        return tool_error(
            error_code="MODEL_NOT_AVAILABLE",
            message="Seedance 适配器未真实接入，请先用 model='kling'",
            hint="待 app/utils/seedance.py 真实化后此路径解禁",
            context={"requested_model": model},
        )

    kling_quality = _VIDEO_QUALITY_MAP.get(quality, "720p")

    from app.utils.evolink import evolink_client

    try:
        task = await evolink_client.text_to_video(
            prompt=prompt,
            duration=duration,
            aspect_ratio=aspect_ratio,
            quality=kling_quality,
        )
    except Exception as exc:
        logger.exception("[media_tools] kling text_to_video 提交异常")
        return tool_error(
            error_code="VIDEO_SUBMIT_FAILED",
            message=f"Kling 任务提交失败：{exc}",
            hint="检查 prompt 是否合规，或稍后重试",
        )

    try:
        finished = await evolink_client.wait_for_completion(
            task.id,
            upload_to_oss=True,
            oss_directory=oss_directory,
        )
    except Exception as exc:
        logger.exception("[media_tools] kling 任务等待异常 task_id=%s", task.id)
        return tool_error(
            error_code="VIDEO_GEN_FAILED",
            message=f"Kling 任务执行失败：{exc}",
            hint="检查任务详情或调整 prompt 后重试",
            context={"task_id": task.id},
        )

    if finished.status != "completed" or not finished.video_url:
        return tool_error(
            error_code="VIDEO_GEN_FAILED",
            message=f"Kling 任务结束但未拿到视频 URL（status={finished.status}）",
            context={"task_id": finished.id, "status": finished.status},
        )

    return {
        "success": True,
        "url": finished.video_url,
        "task_id": finished.id,
        "model": "kling",
        "duration": finished.video_duration or duration,
        "aspect_ratio": aspect_ratio,
        "quality": kling_quality,
    }
