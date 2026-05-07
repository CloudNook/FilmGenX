"""
Seedance 视频生成客户端 —— 占位实现。

当前 Seedance SDK / API 还未在本工程接入。本模块先给定接口契约，与 evolink 对齐
（``text_to_video`` / ``image_to_video`` + 异步 task 轮询 + ``upload_to_oss``
后处理），后续真正接入时只需替换 NotImplementedError 内部实现。

签名严格对齐 [`app/utils/evolink.py`](evolink.py)，让 ``app/core/tools/media_tools.py``
未来加 ``generate_video_seedance_*`` 工具时直接复用 evolink 工具的代码骨架。
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import List, Optional

logger = logging.getLogger(__name__)


@dataclass
class VideoTask:
    """Seedance 视频任务（与 evolink.VideoTask 字段对齐）。"""

    id: str
    status: str  # pending / running / completed / failed
    video_url: Optional[str] = None
    error: Optional[str] = None


class SeedanceClient:
    """Seedance 视频生成客户端。

    .. warning::
        目前所有方法都抛 ``NotImplementedError``。真正接入 Seedance API 时按
        evolink 模式实现：HTTP 提交任务 → 拿 task_id → 轮询状态 → 完成时拿到
        video_url（24h 临时）→ 可选下载并 upload_to_oss 拿永久 URL。
    """

    async def text_to_video(
        self,
        *,
        prompt: str,
        duration: int = 5,
        aspect_ratio: str = "16:9",
        quality: str = "std",
        negative_prompt: Optional[str] = None,
    ) -> VideoTask:
        """文生视频。接口签名对齐 evolink.text_to_video。"""
        raise NotImplementedError(
            "Seedance text_to_video 尚未接入。请使用 app.utils.evolink 走 Kling。"
        )

    async def image_to_video(
        self,
        *,
        prompt: str,
        image_start: str,
        image_end: Optional[str] = None,
        image_urls: Optional[List[str]] = None,
        duration: int = 5,
        aspect_ratio: str = "16:9",
        quality: str = "std",
        negative_prompt: Optional[str] = None,
    ) -> VideoTask:
        """图生视频。接口签名对齐 evolink.image_to_video。"""
        raise NotImplementedError(
            "Seedance image_to_video 尚未接入。请使用 app.utils.evolink 走 Kling。"
        )

    async def wait_for_completion(
        self,
        task_id: str,
        *,
        upload_to_oss: bool = False,
        oss_directory: Optional[str] = None,
        oss_filename: Optional[str] = None,
        max_wait_seconds: int = 600,
    ) -> VideoTask:
        """轮询 task 状态直到完成。接口签名对齐 evolink.wait_for_completion。"""
        raise NotImplementedError(
            "Seedance wait_for_completion 尚未接入。"
        )


# 全局单例（占位，调用任意方法都会抛 NotImplementedError）
seedance_client = SeedanceClient()
