"""
Seedance 2.0 视频生成客户端（reference-to-video）。

Seedance 与 Kling 同样托管在 ``api.evolink.ai``，复用 ``EVOLINK_API_KEY`` /
``EVOLINK_BASE_URL``。区别仅在 ``model`` 字段以及一组 Seedance 特有的入参：

  - ``image_urls``  : 参考图列表（0-9 张），用 prompt 里的自然语言指代用途
  - ``video_urls``  : 运镜 / 动作参考视频（0-3 个）
  - ``audio_urls``  : 背景音 / 对白参考（0-3 个，不能单独提供）
  - ``generate_audio`` : 是否生成同步音频，默认 True
  - ``quality``     : "480p" / "720p"（默认）/ "1080p"
  - ``aspect_ratio``: "16:9"（默认）/ "9:16" / "1:1" / "4:3" / "3:4" / "21:9" / "adaptive"
  - ``duration``    : 4-15 秒，默认 5

文档：https://docs.evolink.ai/en/api-manual/video-series/seedance2.0/seedance-2.0-reference-to-video

使用方式::

    from app.utils.seedance import seedance_client

    task = await seedance_client.image_to_video(
        prompt="角色冲入云海，使用参考图 1 的服装风格",
        image_urls=["https://oss.example.com/character_ref.png"],
        duration=8,
        quality="1080p",
        aspect_ratio="16:9",
    )
    finished = await seedance_client.wait_for_completion(task.id, upload_to_oss=True)
    print(finished.video_url)
"""

from __future__ import annotations

import asyncio
import logging
from typing import Optional

import httpx
from pydantic import BaseModel, Field

from app.core.config import settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 常量
# ---------------------------------------------------------------------------

IMAGE_TO_VIDEO_MODEL = "seedance-2.0-reference-to-video"

# 允许值（来自文档；服务端最终校验，但提前 raise 让上层错误更清晰）
_ALLOWED_QUALITY = {"480p", "720p", "1080p"}
_ALLOWED_ASPECT_RATIO = {"16:9", "9:16", "1:1", "4:3", "3:4", "21:9", "adaptive"}
_MAX_IMAGE_URLS = 9
_MAX_VIDEO_URLS = 3
_MAX_AUDIO_URLS = 3
_MAX_PROMPT_LEN = 500
_MIN_DURATION = 4
_MAX_DURATION = 15


# ---------------------------------------------------------------------------
# Pydantic 数据模型（结构对齐 evolink.VideoTask，让上层切换无痛）
# ---------------------------------------------------------------------------


class TaskInfo(BaseModel):
    can_cancel: Optional[bool] = None
    estimated_time: Optional[float] = None
    video_duration: Optional[float] = None


class Usage(BaseModel):
    """Seedance 计费信息（创建任务时返回）。"""

    billing_rule: Optional[str] = None
    credits_reserved: Optional[float] = None
    user_group: Optional[str] = None


class VideoTask(BaseModel):
    """任务创建 / 状态查询返回。字段命名对齐 evolink.VideoTask。"""

    id: str = Field(..., description="任务 ID")
    status: str = Field(..., description="pending / processing / completed / failed")
    progress: int = Field(0, description="进度 0-100")
    model: Optional[str] = None
    created: Optional[int] = None
    video_duration: Optional[float] = None
    task_info: Optional[TaskInfo] = None
    usage: Optional[Usage] = None
    video_url: Optional[str] = None
    results: list[str] = Field(default_factory=list, description="视频 URL 列表（completed 后有值，24h 有效）")


# ---------------------------------------------------------------------------
# SeedanceClient
# ---------------------------------------------------------------------------


class SeedanceClient:
    """Seedance 2.0 异步客户端。

    Auth：复用 ``EVOLINK_API_KEY``（Seedance 与 Kling 同一 Evolink 网关）。
    所有方法均为 async，适合在 FastAPI / Celery asyncio 环境中使用。
    """

    def __init__(self) -> None:
        self._client: Optional[httpx.AsyncClient] = None
        self._client_loop: Optional[asyncio.AbstractEventLoop] = None

    # -----------------------------------------------------------------------
    # HTTP client 生命周期（与 evolink.py 同款；重复以保持各 client 独立连接池）
    # -----------------------------------------------------------------------

    def _get_client(self) -> httpx.AsyncClient:
        current_loop = asyncio.get_running_loop()

        if self._client is not None:
            loop_changed = self._client_loop is not current_loop
            loop_closed = bool(self._client_loop and self._client_loop.is_closed())
            if self._client.is_closed or loop_changed or loop_closed:
                logger.debug(
                    "重建 Seedance HTTP 客户端：client_closed=%s loop_changed=%s loop_closed=%s",
                    self._client.is_closed,
                    loop_changed,
                    loop_closed,
                )
                self._client = None
                self._client_loop = None

        if self._client is None:
            if not settings.EVOLINK_API_KEY:
                raise RuntimeError(
                    "EVOLINK_API_KEY 未配置（Seedance 复用 Evolink 网关），请在 .env 中填写"
                )
            self._client = httpx.AsyncClient(
                base_url=settings.EVOLINK_BASE_URL.rstrip("/"),
                headers={
                    "Authorization": f"Bearer {settings.EVOLINK_API_KEY}",
                    "Content-Type": "application/json",
                },
                timeout=60.0,
                trust_env=False,
            )
            self._client_loop = current_loop
        return self._client

    async def close(self) -> None:
        try:
            if self._client and not self._client.is_closed:
                await self._client.aclose()
        except RuntimeError as exc:
            if "Event loop is closed" not in str(exc):
                raise
            logger.warning("关闭 Seedance HTTP 客户端时跳过已关闭事件循环: %s", exc)
        finally:
            self._client = None
            self._client_loop = None

    async def _request(self, method: str, url: str, **kwargs) -> httpx.Response:
        max_attempts = max(1, settings.EVOLINK_REQUEST_RETRIES)
        last_error: Optional[httpx.RequestError] = None

        for attempt in range(1, max_attempts + 1):
            try:
                return await self._get_client().request(method, url, **kwargs)
            except httpx.RequestError as exc:
                last_error = exc
                if attempt >= max_attempts:
                    break
                logger.warning(
                    "Seedance 请求异常，准备重试：method=%s url=%s attempt=%d/%d error=%s",
                    method, url, attempt, max_attempts, exc,
                )
                await self.close()
                await asyncio.sleep(min(4.0, float(attempt)))

        assert last_error is not None
        raise ConnectionError(f"Seedance 请求失败：{method} {url} ({last_error})") from last_error

    def _raise_for_status(self, response: httpx.Response) -> None:
        if response.status_code == 200:
            return
        code = response.status_code
        try:
            detail = response.json()
        except Exception:
            detail = response.text
        if code == 401:
            raise PermissionError(f"EVOLINK_API_KEY 无效或已过期。{detail}")
        if code == 402:
            raise RuntimeError(f"Evolink 账户余额不足。{detail}")
        if code == 429:
            raise RuntimeError(f"Seedance 请求频率超限，请稍后重试。{detail}")
        raise RuntimeError(f"Seedance API 错误 {code}: {detail}")

    @staticmethod
    def _parse_task(data: dict) -> VideoTask:
        task_info_raw = data.get("task_info") or {}
        task_info = (
            TaskInfo(**{k: v for k, v in task_info_raw.items() if k in TaskInfo.model_fields})
            if task_info_raw
            else None
        )

        usage_raw = data.get("usage") or {}
        usage = (
            Usage(**{k: v for k, v in usage_raw.items() if k in Usage.model_fields})
            if usage_raw
            else None
        )

        results: list[str] = data.get("results") or []
        video_url = results[0] if results else None

        return VideoTask(
            id=data["id"],
            status=data.get("status", "pending"),
            progress=data.get("progress", 0),
            model=data.get("model"),
            created=data.get("created"),
            video_duration=data.get("video_duration"),
            task_info=task_info,
            usage=usage,
            video_url=video_url,
            results=results,
        )

    # -----------------------------------------------------------------------
    # 公开 API
    # -----------------------------------------------------------------------

    async def image_to_video(
        self,
        *,
        prompt: str,
        image_urls: Optional[list[str]] = None,
        video_urls: Optional[list[str]] = None,
        audio_urls: Optional[list[str]] = None,
        duration: int = 5,
        quality: str = "1080p",
        aspect_ratio: str = "16:9",
        generate_audio: bool = True,
        callback_url: Optional[str] = None,
    ) -> VideoTask:
        """Seedance 2.0 reference-to-video。

        至少需要一项媒体输入（``image_urls`` / ``video_urls``），``audio_urls`` 不能
        单独提供。``prompt`` 中通过 ``"reference image 1"`` / ``"video 1"`` / ``"audio 1"``
        这种自然语言索引来指代各路素材的用途（保持 Seedance 文档建议的用法）。

        Args:
            prompt:          画面 / 行为描述（≤500 字符；中英文都可以）。
            image_urls:      参考图 URL 列表（0-9 张；.jpeg/.png/.webp；300-6000px；
                             长宽比 0.4-2.5；≤30MB/张）。
            video_urls:      运镜 / 动作参考视频列表（0-3 个；.mp4/.mov；单段 2-15s，
                             总长 ≤15s；480p/720p/1080p；≤50MB/个）。
            audio_urls:      背景音 / 对白参考列表（0-3 段；.wav/.mp3；单段 2-15s，
                             总长 ≤15s；≤15MB/段）。**不能在没有图 / 视频时单独使用。**
            duration:        视频总时长（秒），4-15，默认 5。
            quality:         分辨率，"480p" / "720p" / "1080p"（默认）。
            aspect_ratio:    画幅比例，默认 "16:9"。允许：16:9 / 9:16 / 1:1 / 4:3
                             / 3:4 / 21:9 / adaptive。
            generate_audio:  是否生成同步音频，默认 True。
            callback_url:    任务完成后的 HTTPS 回调地址（可选）。

        Returns:
            初始 ``VideoTask``（status=pending），用 ``wait_for_completion`` 拿成品。
        """
        self._validate_image_to_video(
            prompt=prompt,
            image_urls=image_urls,
            video_urls=video_urls,
            audio_urls=audio_urls,
            duration=duration,
            quality=quality,
            aspect_ratio=aspect_ratio,
        )

        payload: dict = {
            "model": IMAGE_TO_VIDEO_MODEL,
            "prompt": prompt,
            "duration": duration,
            "quality": quality,
            "aspect_ratio": aspect_ratio,
            "generate_audio": generate_audio,
        }
        if image_urls:
            payload["image_urls"] = list(image_urls)
        if video_urls:
            payload["video_urls"] = list(video_urls)
        if audio_urls:
            payload["audio_urls"] = list(audio_urls)
        if callback_url:
            payload["callback_url"] = callback_url

        import json as _json
        logger.info("Seedance 请求 payload: %s", _json.dumps(payload, ensure_ascii=False, indent=2))

        response = await self._request("POST", "/v1/videos/generations", json=payload)
        self._raise_for_status(response)
        return self._parse_task(response.json())

    @staticmethod
    def _validate_image_to_video(
        *,
        prompt: str,
        image_urls: Optional[list[str]],
        video_urls: Optional[list[str]],
        audio_urls: Optional[list[str]],
        duration: int,
        quality: str,
        aspect_ratio: str,
    ) -> None:
        if not prompt or not prompt.strip():
            raise ValueError("prompt 不能为空")
        if len(prompt) > _MAX_PROMPT_LEN:
            raise ValueError(f"prompt 超过 {_MAX_PROMPT_LEN} 字符上限（当前 {len(prompt)}）")

        has_image = bool(image_urls)
        has_video = bool(video_urls)
        has_audio = bool(audio_urls)

        if has_audio and not (has_image or has_video):
            # 文档明确：audio_urls 不能单独提供
            raise ValueError("audio_urls 不能单独提供，必须搭配 image_urls 或 video_urls")
        if not has_image and not has_video:
            raise ValueError("Seedance reference-to-video 至少需要 image_urls 或 video_urls 中的一项")

        if image_urls and len(image_urls) > _MAX_IMAGE_URLS:
            raise ValueError(f"image_urls 最多 {_MAX_IMAGE_URLS} 张（当前 {len(image_urls)}）")
        if video_urls and len(video_urls) > _MAX_VIDEO_URLS:
            raise ValueError(f"video_urls 最多 {_MAX_VIDEO_URLS} 个（当前 {len(video_urls)}）")
        if audio_urls and len(audio_urls) > _MAX_AUDIO_URLS:
            raise ValueError(f"audio_urls 最多 {_MAX_AUDIO_URLS} 段（当前 {len(audio_urls)}）")

        if not (_MIN_DURATION <= duration <= _MAX_DURATION):
            raise ValueError(f"duration 必须在 {_MIN_DURATION}-{_MAX_DURATION} 秒（当前 {duration}）")
        if quality not in _ALLOWED_QUALITY:
            raise ValueError(f"quality 必须是 {sorted(_ALLOWED_QUALITY)} 之一（当前 {quality!r}）")
        if aspect_ratio not in _ALLOWED_ASPECT_RATIO:
            raise ValueError(
                f"aspect_ratio 必须是 {sorted(_ALLOWED_ASPECT_RATIO)} 之一（当前 {aspect_ratio!r}）"
            )

    async def text_to_video(self, **_kwargs) -> VideoTask:
        """文生视频（Seedance text-to-video 待接入）。

        当前文档只覆盖 reference-to-video；text-to-video 接入时按同样模式实现即可。
        """
        raise NotImplementedError(
            "Seedance text_to_video 尚未接入；请用 image_to_video 或回退 evolink"
        )

    async def get_task(self, task_id: str) -> VideoTask:
        """查询任务状态。Evolink 网关下 Seedance / Kling 共用同一 task 接口。"""
        response = await self._request("GET", f"/v1/tasks/{task_id}")
        self._raise_for_status(response)
        return self._parse_task(response.json())

    async def wait_for_completion(
        self,
        task_id: str,
        poll_interval: float = 5.0,
        *,
        upload_to_oss: bool = False,
        oss_directory: Optional[str] = None,
        oss_filename: Optional[str] = None,
        max_wait_seconds: float = 1200.0,
    ) -> VideoTask:
        """轮询任务直到完成 / 失败 / 超过 ``max_wait_seconds``。

        Args:
            task_id:           要等待的任务 ID。
            poll_interval:     每次轮询间隔（秒），默认 5。
            upload_to_oss:     完成后是否下载视频并上传 OSS 拿永久 URL。
            oss_directory:     OSS 目标目录，如 ``"videos/shots"``。
            oss_filename:      OSS 文件名，如 ``"shot_001.mp4"``。
            max_wait_seconds:  最长等待时长（秒），默认 1200（=20 分钟）；超时抛
                               ``TimeoutError``，避免上游卡死任务。

        Returns:
            完成的 ``VideoTask``。``upload_to_oss=True`` 时 ``video_url`` 为永久 URL。

        Raises:
            RuntimeError:  任务以 failed 状态结束。
            TimeoutError:  超过 ``max_wait_seconds`` 仍未完成。
        """
        loop = asyncio.get_event_loop()
        deadline = loop.time() + max_wait_seconds

        while True:
            if loop.time() >= deadline:
                raise TimeoutError(
                    f"Seedance 任务 {task_id} 超过 {max_wait_seconds:.0f}s 未完成"
                )

            try:
                task = await self.get_task(task_id)
            except ConnectionError as exc:
                logger.warning(
                    "Seedance 任务轮询网络异常，继续重试：task_id=%s error=%s",
                    task_id, exc,
                )
                await asyncio.sleep(poll_interval)
                continue

            logger.debug(
                "Seedance 任务 %s 状态: %s  进度: %s%%",
                task_id, task.status, task.progress,
            )
            if task.status == "completed":
                if upload_to_oss and task.video_url:
                    from app.utils.oss import oss_client
                    permanent_url = oss_client.download_and_upload(
                        task.video_url,
                        directory=oss_directory,
                        filename=oss_filename,
                    )
                    logger.info("Seedance 视频已上传到 OSS：%s", permanent_url)
                    task = task.model_copy(update={
                        "video_url": permanent_url,
                        "results": [permanent_url],
                    })
                return task
            if task.status == "failed":
                raise RuntimeError(f"Seedance 任务 {task_id} 失败")
            await asyncio.sleep(poll_interval)


# 全局单例，直接 import 使用
seedance_client = SeedanceClient()
