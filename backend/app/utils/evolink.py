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

    # GPT-Image-2 图像生成（文生图 / 图生图统一）
    img_task = await evolink_client.image_generation(
        prompt="一只穿宇航服的猫漂浮在太空中",
        resolution="2K",
        quality="high",
        n=2,
    )

    # 轮询任务状态（image / video 共用同一个 wait_for_completion）
    result = await evolink_client.wait_for_completion(
        task.id,
        upload_to_oss=True,
        oss_directory="workspace/videos",
        oss_filename_prefix="shot-001",
    )
    if result.status == "completed":
        print(result.results)   # 全部产物 URL（image: N 张 / video: 通常 1 个）
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
GPT_IMAGE_2_MODEL = "gpt-image-2"

# GPT-Image-2 允许的枚举值（来自官方 doc；服务端最终校验，提前 raise 让上层错误更清晰）
_GPT_IMAGE_RESOLUTIONS = {"1K", "2K", "4K"}
_GPT_IMAGE_QUALITIES = {"low", "medium", "high"}
_GPT_IMAGE_MAX_PROMPT_LEN = 32000
_GPT_IMAGE_MAX_N = 10
_GPT_IMAGE_MAX_REF_IMAGES = 16


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
    # video 任务在 task_info 里返回 video_duration；image 任务没有
    video_duration: Optional[float] = None


class TaskUsage(BaseModel):
    """Evolink 任务计费信息（创建任务时返回，image / video 共用形态）。"""
    billing_rule: Optional[str] = None       # per_call / per_token / per_second
    credits_reserved: Optional[float] = None
    user_group: Optional[str] = None


class EvolinkTask(BaseModel):
    """Evolink 任务对象（image / video 共用）。

    Evolink 网关把图像与视频任务形态完全对齐，``type`` 字段是唯一区分：
    ``"image"`` 时 ``results`` 是 N 张图片 URL（长度 = 入参 n）；
    ``"video"`` 时 ``results`` 通常 1 个视频 URL。
    所有 URL **24 小时失效**，要存就 ``upload_to_oss=True`` 转 OSS 永久链接。

    历史代码里有 ``VideoTask`` / ``ImageTask`` 两个名字 → 现在都是本类的别名。
    """
    id: str = Field(..., description="任务 ID")
    status: str = Field(..., description="pending / processing / completed / failed")
    progress: int = Field(0, description="进度 0-100")
    model: Optional[str] = None
    created: Optional[int] = None
    type: Optional[str] = Field(None, description='"image" 或 "video"，网关自动设置')
    object: Optional[str] = Field(None, description='"image.generation.task" / "video.generation.task"')
    task_info: Optional[TaskInfo] = None
    usage: Optional[TaskUsage] = None
    results: list[str] = Field(default_factory=list, description="产物 URL 列表（completed 后有值，24h 失效）")

    # 向下兼容字段：仅 video 任务顶层会带 video_duration（Kling 风格响应）；
    # video_url / image_url 是 results[0] 的便捷别名，让现有调用方少改。
    video_duration: Optional[float] = None
    video_url: Optional[str] = None
    image_url: Optional[str] = None

    # 失败原因。Evolink 在 status=failed 时通常会带 error / error_message / failure_reason
    # 等字段；我们尽力解析并透传给上层，否则 task.status=failed 时调用方只能看到
    # "任务失败" 而不知道是审核/尺寸/拉图失败等真实原因。
    error: Optional[str] = None

    @property
    def url(self) -> Optional[str]:
        """统一便捷访问 ``results[0]``。type=image/video 都返同样语义的第一个产物 URL。"""
        return self.results[0] if self.results else None


# 向下兼容别名：上游 import VideoTask / ImageTask 的地方继续可用
VideoTask = EvolinkTask
ImageTask = EvolinkTask
# 旧 ImageUsage 别名（生成图像时返回的 usage 块原叫这个，现已合并到 TaskUsage）
ImageUsage = TaskUsage


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
                trust_env=False,
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
            import json
            logger.info("multi_shot_prompts: %s", json.dumps([p.model_dump() for p in multi_shot_prompts], ensure_ascii=False, indent=2))
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

        import json as _json
        logger.info("Evolink 请求 payload: %s", _json.dumps(payload, ensure_ascii=False, indent=2))
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
    def _parse_task(data: dict) -> EvolinkTask:
        """从响应 JSON 解析 ``EvolinkTask``（image / video 共用）。

        Evolink 网关把两种任务形态对齐，只看 ``type`` 字段区分：
          - results: [url, ...]   产物 URL 列表（image n=多张 / video 通常 1 张）
          - type:                 "image" / "video"
          - task_info:            { can_cancel, estimated_time, video_duration? }
          - usage:                { billing_rule, credits_reserved, user_group }
          - video_duration:       仅 Kling 视频任务顶层附带（其它 None）
        """
        task_info_raw = data.get("task_info") or {}
        task_info = (
            TaskInfo(**{k: v for k, v in task_info_raw.items() if k in TaskInfo.model_fields})
            if task_info_raw
            else None
        )

        usage_raw = data.get("usage") or {}
        usage = (
            TaskUsage(**{k: v for k, v in usage_raw.items() if k in TaskUsage.model_fields})
            if usage_raw
            else None
        )

        results: list[str] = data.get("results") or []
        first_url = results[0] if results else None
        task_type = data.get("type")  # "image" / "video" / None

        # 解析失败原因：不同上游模型字段名不统一，按常见顺序兜底取。
        # error 可能是字符串，也可能是 {"message": "...", "code": "..."} 这样的对象。
        error_raw = (
            data.get("error")
            or data.get("error_message")
            or data.get("failure_reason")
            or data.get("message")
        )
        if isinstance(error_raw, dict):
            error_text = (
                error_raw.get("message")
                or error_raw.get("error")
                or error_raw.get("reason")
                or str(error_raw)
            )
        elif error_raw is not None:
            error_text = str(error_raw)
        else:
            error_text = None

        return EvolinkTask(
            id=data["id"],
            status=data.get("status", "pending"),
            progress=data.get("progress", 0),
            model=data.get("model"),
            created=data.get("created"),
            type=task_type,
            object=data.get("object"),
            task_info=task_info,
            usage=usage,
            results=results,
            video_duration=data.get("video_duration"),
            # 按 type 填便捷字段：让现有 `task.video_url` / `task.image_url` 调用方继续可用
            video_url=first_url if task_type == "video" else None,
            image_url=first_url if task_type == "image" else None,
            error=error_text,
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
            # "callback_url": callback_url,
            "model_params": model_params,
        }
        return await self._post_generation(payload)

    async def get_task(self, task_id: str) -> EvolinkTask:
        """查询任务状态（image / video 共用）。

        Args:
            task_id: ``image_generation`` / ``text_to_video`` / ``image_to_video`` 返回的任务 ID。

        Returns:
            ``EvolinkTask``，status 为 completed 时 ``results`` 有值（URL 24 小时有效）。

        Note:
            Evolink 网关统一任务查询端点: ``GET /v1/tasks/{task_id}``，
            image / video 任务形态对齐，仅 ``type`` 字段区分。
        """
        response = await self._request("GET", f"/v1/tasks/{task_id}")
        self._raise_for_status(response)
        return self._parse_task(response.json())

    # -----------------------------------------------------------------------
    # GPT-Image-2 图像生成（同样走 Evolink 网关 + 异步 task 轮询）
    # -----------------------------------------------------------------------

    async def image_generation(
        self,
        *,
        prompt: str,
        image_urls: Optional[list[str]] = None,
        size: Optional[str] = None,
        resolution: str = "1K",
        quality: str = "medium",
        n: int = 1,
        callback_url: Optional[str] = None,
    ) -> EvolinkTask:
        """GPT-Image-2 图像生成（文生图 / 图生图 / 编辑统一接口）。

        ``image_urls`` 不传 → 纯 text-to-image；传 1-16 张 → 走 image-to-image
        / 编辑（具体语义由 prompt 决定，如 "Add a cute cat next to her"）。

        Args:
            prompt:        画面描述或编辑指令（≤32000 字符；中英文都行）。
            image_urls:    参考图 URL 列表（0-16 张；.jpeg/.jpg/.png/.webp；≤50MB/张）。
                           可传则走 image-to-image / 编辑；不传则纯文生图。
            size:          画幅，支持比例（"1:1" / "16:9"）或显式像素（"1024x1024"）。
                           ``None`` / ``"auto"`` 让模型自决；显式像素时 ``resolution`` 忽略。
            resolution:    分辨率档位 ``"1K"`` / ``"2K"`` / ``"4K"``，默认 ``"1K"``。
            quality:       渲染质量 ``"low"`` / ``"medium"``（默认）/ ``"high"``。
                           更高耗费更多 credit。
            n:             生成张数，1-10，默认 1。
            callback_url:  HTTPS 回调地址（可选）。

        Returns:
            初始 ``EvolinkTask``（status=pending, type="image"），用 ``wait_for_completion``
            拿成品 URL。

        Note:
            生成的图片 URL 24 小时失效，需及时下载或 ``upload_to_oss=True`` 转永久 URL。
        """
        self._validate_image_generation(
            prompt=prompt,
            image_urls=image_urls,
            resolution=resolution,
            quality=quality,
            n=n,
        )

        payload: dict = {
            "model": GPT_IMAGE_2_MODEL,
            "prompt": prompt,
            "resolution": resolution,
            "quality": quality,
            "n": n,
        }
        if size:
            payload["size"] = size
        if image_urls:
            payload["image_urls"] = list(image_urls)
        if callback_url:
            payload["callback_url"] = callback_url

        import json as _json
        logger.info("Evolink GPT-Image-2 请求 payload: %s", _json.dumps(payload, ensure_ascii=False, indent=2))

        response = await self._request("POST", "/v1/images/generations", json=payload)
        self._raise_for_status(response)
        return self._parse_task(response.json())

    @staticmethod
    def _validate_image_generation(
        *,
        prompt: str,
        image_urls: Optional[list[str]],
        resolution: str,
        quality: str,
        n: int,
    ) -> None:
        if not prompt or not prompt.strip():
            raise ValueError("prompt 不能为空")
        if len(prompt) > _GPT_IMAGE_MAX_PROMPT_LEN:
            raise ValueError(
                f"prompt 超过 {_GPT_IMAGE_MAX_PROMPT_LEN} 字符上限（当前 {len(prompt)}）"
            )
        if image_urls is not None and len(image_urls) > _GPT_IMAGE_MAX_REF_IMAGES:
            raise ValueError(
                f"image_urls 最多 {_GPT_IMAGE_MAX_REF_IMAGES} 张（当前 {len(image_urls)}）"
            )
        if not (1 <= n <= _GPT_IMAGE_MAX_N):
            raise ValueError(f"n 必须在 1-{_GPT_IMAGE_MAX_N}（当前 {n}）")
        if resolution not in _GPT_IMAGE_RESOLUTIONS:
            raise ValueError(
                f"resolution 必须是 {sorted(_GPT_IMAGE_RESOLUTIONS)} 之一（当前 {resolution!r}）"
            )
        if quality not in _GPT_IMAGE_QUALITIES:
            raise ValueError(
                f"quality 必须是 {sorted(_GPT_IMAGE_QUALITIES)} 之一（当前 {quality!r}）"
            )

    async def wait_for_completion(
        self,
        task_id: str,
        poll_interval: float = 5.0,
        *,
        upload_to_oss: bool = False,
        oss_directory: Optional[str] = None,
        oss_filename_prefix: Optional[str] = None,
        max_wait_seconds: Optional[float] = None,
    ) -> EvolinkTask:
        """轮询任务直到完成 / 失败 / 超过 ``max_wait_seconds``（image / video 共用）。

        Evolink 网关把图像与视频任务对齐到同一接口 ``/v1/tasks/{id}``，仅 ``type``
        区分。本方法对两种任务都适用——OSS 上传时 ``task.results`` 里全部 URL 一起转。

        Args:
            task_id:             ``image_generation`` / ``text_to_video`` / ``image_to_video``
                                 返回的任务 ID。
            poll_interval:       每次轮询间隔（秒），默认 5。图像通常 10-60s，视频更长。
            upload_to_oss:       完成后是否把所有 ``results`` 下载并上传 OSS 转永久 URL。
            oss_directory:       OSS 目标目录，如 ``"workspace/images"`` / ``"supervisor/videos"``。
            oss_filename_prefix: OSS 文件名前缀。
                                 - 视频 / 单图（n=1）：用前缀作为文件名，扩展名按 ``type`` 自动推断
                                   （image→.png, video→.mp4）。
                                 - 多图（n>1）：每张在尾部加 ``-1`` / ``-2`` 后缀。
                                 ``None`` 时由 OSS 客户端按 URL 自动命名。
            max_wait_seconds:    最长等待时长（秒）。``None``（默认）= 不超时（视频常用）；
                                 显式传值时超时抛 ``TimeoutError``。

        Returns:
            完成的 ``EvolinkTask``。``upload_to_oss=True`` 时 ``results`` 全部为永久 URL；
            ``video_url`` / ``image_url`` 便捷字段也同步更新。

        Raises:
            RuntimeError:  任务以 failed 状态结束。
            TimeoutError:  ``max_wait_seconds`` 设了值且超过仍未完成。
        """
        loop = asyncio.get_event_loop()
        deadline = (loop.time() + max_wait_seconds) if max_wait_seconds is not None else None

        while True:
            if deadline is not None and loop.time() >= deadline:
                raise TimeoutError(
                    f"Evolink 任务 {task_id} 超过 {max_wait_seconds:.0f}s 未完成"
                )

            try:
                task = await self.get_task(task_id)
            except ConnectionError as exc:
                logger.warning(
                    "Evolink 任务轮询网络异常，继续重试：task_id=%s error=%s",
                    task_id, exc,
                )
                await asyncio.sleep(poll_interval)
                continue

            logger.debug(
                "Evolink 任务 %s (type=%s) 状态: %s  进度: %s%%",
                task_id, task.type, task.status, task.progress,
            )

            if task.status == "completed":
                if upload_to_oss and task.results:
                    permanent_urls = await self._upload_results_to_oss(
                        task=task,
                        directory=oss_directory,
                        filename_prefix=oss_filename_prefix,
                    )
                    task = task.model_copy(update={
                        "results": permanent_urls,
                        "image_url": permanent_urls[0] if task.type == "image" else None,
                        "video_url": permanent_urls[0] if task.type == "video" else None,
                    })
                return task

            if task.status == "failed":
                reason = task.error or "(网关未返回具体原因)"
                raise RuntimeError(f"Evolink 任务 {task_id} 失败: {reason}")

            await asyncio.sleep(poll_interval)

    @staticmethod
    async def _upload_results_to_oss(
        *,
        task: EvolinkTask,
        directory: Optional[str],
        filename_prefix: Optional[str],
    ) -> list[str]:
        """把 ``task.results`` 全部下载并上传 OSS，返回永久 URL 列表。

        命名规则（仅当 ``filename_prefix`` 给出时）：
        - 单 URL：``{prefix}.{ext}``
        - 多 URL：``{prefix}-1.{ext}`` / ``{prefix}-2.{ext}`` ...
        扩展名按 ``task.type`` 推断：image → png，video → mp4。
        """
        from app.utils.oss import oss_client

        ext = "png" if task.type == "image" else "mp4"
        permanent_urls: list[str] = []
        n = len(task.results)

        for idx, url in enumerate(task.results, start=1):
            filename = None
            if filename_prefix:
                suffix = f"-{idx}" if n > 1 else ""
                filename = f"{filename_prefix}{suffix}.{ext}"
            permanent = oss_client.download_and_upload(
                url,
                directory=directory,
                filename=filename,
            )
            permanent_urls.append(permanent)

        logger.info(
            "Evolink 任务 %s 已上传 %d 个产物到 OSS：%s",
            task.id, len(permanent_urls), permanent_urls,
        )
        return permanent_urls


# 全局单例，直接 import 使用
evolink_client = EvolinkClient()
