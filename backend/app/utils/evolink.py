"""
Evolink（Kling AI）视频生成工具。

支持：
  - 文生视频（kling-o3-text-to-video）
  - 图生视频（kling-o3-image-to-video），支持 image_start / image_end / 参考图
  - 多镜头模式（multi_shot），最多 6 个镜头
  - 任务状态查询

使用方式：
    from app.utils.evolink import evolink_client, MultiShotPrompt

    # 文生视频（单镜头）
    task = await evolink_client.text_to_video(
        prompt="一个穿着白袍的少年站在悬崖边，俯瞰云海",
        duration=5,
        aspect_ratio="16:9",
        quality="1080p",
    )

    # 文生视频（多镜头）
    task = await evolink_client.text_to_video(
        multi_shot_prompts=[
            MultiShotPrompt(index=1, prompt="镜头一描述", duration="3"),
            MultiShotPrompt(index=2, prompt="镜头二描述", duration="2"),
        ],
        duration=5,
    )

    # 图生视频（首帧 + 参考图）
    task = await evolink_client.image_to_video(
        prompt="角色飞速冲向天空，使用 <<<image_1>>> 的风格",
        image_start="https://oss.example.com/shot001.png",
        image_urls=["https://oss.example.com/style_ref.png"],
    )

    # 轮询任务状态
    result = await evolink_client.get_task(task.id)
    if result.status == "completed":
        print(result.video_url)
"""

import asyncio
import logging
from typing import Optional

import httpx
from pydantic import BaseModel, Field

from app.core.config import settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Pydantic 数据模型
# ---------------------------------------------------------------------------

TEXT_TO_VIDEO_MODEL = "kling-o3-text-to-video"
IMAGE_TO_VIDEO_MODEL = "kling-o3-image-to-video"


class MultiShotPrompt(BaseModel):
    """多镜头模式中单个镜头的描述。"""
    index: int = Field(..., description="镜头序号，从 1 开始")
    prompt: str = Field(..., max_length=512, description="该镜头的画面描述（最多 512 字符）")
    duration: str = Field(..., description="该镜头时长（秒），字符串格式，如 '3'")


class WatermarkInfo(BaseModel):
    enabled: bool = False


class ModelParams(BaseModel):
    """model_params 结构，文生/图生共用。"""
    multi_shot: Optional[bool] = None
    shot_type: Optional[str] = None          # multi_shot=True 时必须为 "customize"
    multi_prompt: Optional[list[MultiShotPrompt]] = None
    watermark_info: Optional[WatermarkInfo] = None


class TaskInfo(BaseModel):
    can_cancel: Optional[bool] = None
    estimated_time: Optional[float] = None   # 预计剩余秒数


class VideoTask(BaseModel):
    """任务创建或查询的返回结果。"""
    id: str = Field(..., description="任务 ID")
    status: str = Field(..., description="pending / processing / completed / failed")
    progress: int = Field(0, description="进度 0-100")
    model: Optional[str] = None
    created: Optional[int] = None
    video_duration: Optional[float] = None   # 视频总时长（秒），顶层字段
    task_info: Optional[TaskInfo] = None
    video_url: Optional[str] = None          # 生成完成后的视频链接（24 小时有效）
    results: list[str] = Field(default_factory=list, description="视频 URL 列表（completed 后有值）")


# ---------------------------------------------------------------------------
# EvolinkClient
# ---------------------------------------------------------------------------

class EvolinkClient:
    """Evolink API 异步客户端。

    通过 EVOLINK_API_KEY 和 EVOLINK_BASE_URL（默认 https://api.evolink.ai）连接服务。
    所有方法均为 async，适合在 FastAPI / Celery asyncio 环境中使用。
    """

    def __init__(self) -> None:
        self._client: Optional[httpx.AsyncClient] = None
        self._client_loop: Optional[asyncio.AbstractEventLoop] = None

    def _get_client(self) -> httpx.AsyncClient:
        """懒加载 httpx 客户端。"""
        current_loop = asyncio.get_running_loop()

        if self._client is not None:
            loop_changed = self._client_loop is not current_loop
            loop_closed = bool(self._client_loop and self._client_loop.is_closed())
            if self._client.is_closed or loop_changed or loop_closed:
                logger.debug(
                    "重建 Evolink HTTP 客户端：client_closed=%s loop_changed=%s loop_closed=%s",
                    self._client.is_closed,
                    loop_changed,
                    loop_closed,
                )
                self._client = None
                self._client_loop = None

        if self._client is None:
            if not settings.EVOLINK_API_KEY:
                raise RuntimeError(
                    "EVOLINK_API_KEY 未配置，请在 .env 中填写"
                )
            self._client = httpx.AsyncClient(
                base_url=settings.EVOLINK_BASE_URL.rstrip("/"),
                headers={
                    "Authorization": f"Bearer {settings.EVOLINK_API_KEY}",
                    "Content-Type": "application/json",
                },
                timeout=60.0,
                trust_env=settings.HTTP_TRUST_ENV,
            )
            self._client_loop = current_loop
        return self._client

    async def close(self) -> None:
        """关闭 HTTP 连接（应用关闭时调用）。"""
        try:
            if self._client and not self._client.is_closed:
                await self._client.aclose()
        except RuntimeError as exc:
            if "Event loop is closed" not in str(exc):
                raise
            logger.warning("关闭 Evolink HTTP 客户端时跳过已关闭事件循环: %s", exc)
        finally:
            self._client = None
            self._client_loop = None

    # -----------------------------------------------------------------------
    # 内部辅助
    # -----------------------------------------------------------------------

    def _build_model_params(
        self,
        multi_shot_prompts: Optional[list[MultiShotPrompt]],
        watermark: bool,
    ) -> Optional[dict]:
        if not multi_shot_prompts and not watermark:
            return None
        params: dict = {}
        if multi_shot_prompts:
            params["multi_shot"] = True
            params["shot_type"] = "customize"
            params["multi_prompt"] = [p.model_dump() for p in multi_shot_prompts]
        if watermark:
            params["watermark_info"] = {"enabled": True}
        return params

    async def _request(self, method: str, url: str, **kwargs) -> httpx.Response:
        """带有限重试的 HTTP 请求。

        Evolink 轮询场景会持续数分钟，期间偶发的代理/TLS/连接抖动不应直接导致整个
        视频任务失败，因此这里对 transport 层错误做短重试，并在重试前重建连接池。
        """
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
                    "Evolink 请求异常，准备重试：method=%s url=%s attempt=%d/%d error=%s",
                    method,
                    url,
                    attempt,
                    max_attempts,
                    exc,
                )
                await self.close()
                await asyncio.sleep(min(4.0, float(attempt)))

        assert last_error is not None
        raise ConnectionError(f"Evolink 请求失败：{method} {url} ({last_error})") from last_error

    async def _post_generation(self, payload: dict) -> VideoTask:
        """发送创建视频任务请求并返回 VideoTask。"""
        # 移除 None 值，保持请求体简洁
        payload = {k: v for k, v in payload.items() if v is not None}
        if "model_params" in payload and payload["model_params"] is None:
            del payload["model_params"]

        logger.debug("Evolink 请求 payload: %s", payload)
        response = await self._request("POST", "/v1/videos/generations", json=payload)
        self._raise_for_status(response)
        return self._parse_task(response.json())

    def _raise_for_status(self, response: httpx.Response) -> None:
        """统一处理 HTTP 错误码。"""
        if response.status_code == 200:
            return
        code = response.status_code
        try:
            detail = response.json()
        except Exception:
            detail = response.text
        msg = f"Evolink API 错误 {code}: {detail}"
        if code == 401:
            raise PermissionError(f"EVOLINK_API_KEY 无效或已过期。{detail}")
        if code == 402:
            raise RuntimeError(f"Evolink 账户余额不足。{detail}")
        if code == 429:
            raise RuntimeError(f"Evolink 请求频率超限，请稍后重试。{detail}")
        raise RuntimeError(msg)

    @staticmethod
    def _parse_task(data: dict) -> VideoTask:
        """从响应 JSON 解析 VideoTask。

        实际响应结构：
          - results: [url, ...]   视频链接数组
          - video_duration:       视频时长，顶层字段
          - task_info:            { can_cancel, estimated_time }
        """
        task_info_raw = data.get("task_info") or {}
        task_info = TaskInfo(**{k: v for k, v in task_info_raw.items() if k in TaskInfo.model_fields}) if task_info_raw else None

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
            video_url=video_url,
            results=results,
        )

    # -----------------------------------------------------------------------
    # 公开 API
    # -----------------------------------------------------------------------

    async def text_to_video(
        self,
        *,
        prompt: Optional[str] = None,
        duration: int = 5,
        aspect_ratio: str = "16:9",
        quality: str = "1080p",
        sound: str = "on",
        callback_url: Optional[str] = None,
        multi_shot_prompts: Optional[list[MultiShotPrompt]] = None,
        watermark: bool = False,
    ) -> VideoTask:
        """文生视频。

        Args:
            prompt:              画面描述（单镜头模式必填；多镜头模式可不填）。
            duration:            视频总时长（秒），3-15，默认 5。
            aspect_ratio:        画幅比例，"16:9" / "9:16" / "1:1"，默认 16:9。
            quality:             分辨率，"720p" / "1080p"，默认 720p。
            sound:               是否生成音效，"on" / "off"，默认 off。
            callback_url:        任务完成后的回调 HTTPS 地址（可选）。
            multi_shot_prompts:  多镜头定义列表（最多 6 个），启用后 prompt 可省略。
            watermark:           是否添加水印，默认 False。

        Returns:
            VideoTask，包含任务 ID 和初始状态。
        """
        if not prompt and not multi_shot_prompts:
            raise ValueError("prompt 和 multi_shot_prompts 不能同时为空")
        if multi_shot_prompts and len(multi_shot_prompts) > 6:
            raise ValueError("multi_shot_prompts 最多支持 6 个镜头")

        model_params = self._build_model_params(multi_shot_prompts, watermark)
        payload: dict = {
            "model": TEXT_TO_VIDEO_MODEL,
            "prompt": prompt if not multi_shot_prompts else None,
            "duration": duration,
            "aspect_ratio": aspect_ratio,
            "quality": quality,
            "sound": sound,
            "callback_url": callback_url,
            "model_params": model_params,
        }
        return await self._post_generation(payload)

    async def image_to_video(
        self,
        *,
        prompt: Optional[str] = None,
        image_start: Optional[str] = None,
        image_end: Optional[str] = None,
        image_urls: Optional[list[str]] = None,
        duration: int = 5,
        aspect_ratio: str = "16:9",
        quality: str = "1080p",
        sound: str = "on",
        callback_url: Optional[str] = None,
        multi_shot_prompts: Optional[list[MultiShotPrompt]] = None,
        watermark: bool = False,
    ) -> VideoTask:
        """图生视频。

        支持三种图片模式（可组合）：
          1. image_start：指定首帧画面。
          2. image_end：指定尾帧画面（需同时提供 image_start）。
          3. image_urls：参考图列表，在 prompt 中用 <<<image_1>>> 引用。

        Args:
            prompt:              画面描述。参考图时使用 <<<image_1>>> 语法引用 image_urls。
                                 多镜头模式下可省略。
            image_start:         首帧图片 URL（JPG/PNG，≤10MB，长宽≥300px）。
            image_end:           尾帧图片 URL（需同时提供 image_start）。
            image_urls:          参考图 URL 列表，在 prompt 中以 <<<image_N>>> 引用。
            duration:            视频总时长（秒），3-15，默认 5。
            aspect_ratio:        画幅比例，"16:9" / "9:16" / "1:1"，默认 16:9。
            quality:             分辨率，"720p" / "1080p"，默认 720p。
            sound:               是否生成音效，"on" / "off"，默认 off。
            callback_url:        任务完成后的回调 HTTPS 地址（可选）。
            multi_shot_prompts:  多镜头定义列表（最多 6 个）。
            watermark:           是否添加水印，默认 False。

        Returns:
            VideoTask，包含任务 ID 和初始状态。
        """
        if not prompt and not multi_shot_prompts:
            raise ValueError("prompt 和 multi_shot_prompts 不能同时为空")
        if image_end and not image_start:
            raise ValueError("使用 image_end 时必须同时提供 image_start")
        if multi_shot_prompts and len(multi_shot_prompts) > 6:
            raise ValueError("multi_shot_prompts 最多支持 6 个镜头")

        model_params = self._build_model_params(multi_shot_prompts, watermark)
        payload: dict = {
            "model": IMAGE_TO_VIDEO_MODEL,
            "prompt": prompt if not multi_shot_prompts else None,
            "image_start": image_start,
            "image_end": image_end,
            "image_urls": image_urls,
            "duration": duration,
            "aspect_ratio": aspect_ratio,
            "quality": quality,
            "sound": sound,
            "callback_url": callback_url,
            "model_params": model_params,
        }
        return await self._post_generation(payload)

    async def get_task(self, task_id: str) -> VideoTask:
        """查询视频生成任务状态。

        Args:
            task_id: text_to_video / image_to_video 返回的任务 ID。

        Returns:
            VideoTask，status 为 completed 时 video_url 有值（24 小时有效）。

        Note:
            Evolink 统一任务查询端点: GET /v1/tasks/{task_id}
        """
        response = await self._request("GET", f"/v1/tasks/{task_id}")
        self._raise_for_status(response)
        return self._parse_task(response.json())

    async def wait_for_completion(
        self,
        task_id: str,
        poll_interval: float = 5.0,
        timeout: float = 600.0,
        *,
        upload_to_oss: bool = False,
        oss_directory: Optional[str] = None,
        oss_filename: Optional[str] = None,
    ) -> VideoTask:
        """轮询任务直到完成或超时。

        Args:
            task_id:       要等待的任务 ID。
            poll_interval: 每次轮询间隔（秒），默认 5 秒。
            timeout:       最大等待时间（秒），默认 600 秒（10 分钟）。
            upload_to_oss: 是否自动下载视频并上传到 OSS（获取永久 URL）。
            oss_directory: OSS 目标目录，如 "videos/shots"。
            oss_filename: OSS 文件名，如 "shot_001.mp4"。

        Returns:
            完成或失败的 VideoTask。如果 upload_to_oss=True，video_url 为永久 URL。

        Raises:
            TimeoutError: 超过 timeout 仍未完成。
            RuntimeError: 任务以 failed 状态结束。
        """
        loop = asyncio.get_running_loop()
        deadline = loop.time() + timeout

        while loop.time() < deadline:
            try:
                task = await self.get_task(task_id)
            except ConnectionError as exc:
                remaining = max(0.0, deadline - loop.time())
                logger.warning(
                    "Evolink 任务轮询异常，将继续重试：task_id=%s remaining=%.1fs error=%s",
                    task_id,
                    remaining,
                    exc,
                )
                if remaining <= 0:
                    break
                await asyncio.sleep(min(poll_interval, remaining))
                continue

            logger.debug(
                "Evolink 任务 %s 状态: %s  进度: %s%%",
                task_id, task.status, task.progress,
            )
            if task.status == "completed":
                # 下载并上传到 OSS
                if upload_to_oss and task.video_url:
                    from app.utils.oss import oss_client
                    permanent_url = oss_client.download_and_upload(
                        task.video_url,
                        directory=oss_directory,
                        filename=oss_filename,
                    )
                    logger.info("视频已上传到 OSS：%s", permanent_url)
                    # 更新返回对象中的 URL
                    task = VideoTask(
                        id=task.id,
                        status=task.status,
                        progress=task.progress,
                        model=task.model,
                        created=task.created,
                        video_duration=task.video_duration,
                        task_info=task.task_info,
                        video_url=permanent_url,
                        results=[permanent_url],
                    )
                return task
            if task.status == "failed":
                raise RuntimeError(f"Evolink 任务 {task_id} 失败")
            remaining = max(0.0, deadline - loop.time())
            if remaining <= 0:
                break
            await asyncio.sleep(min(poll_interval, remaining))

        raise TimeoutError(f"Evolink 任务 {task_id} 超时（{timeout}s）")


# 全局单例，直接 import 使用
evolink_client = EvolinkClient()
