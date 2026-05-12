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

import asyncio
import logging
from typing import Any, Dict, Optional

from app.core.agent.tool_errors import tool_error
from app.core.tools.registry import register_tool

logger = logging.getLogger(__name__)


_DEFAULT_IMAGE_DIR = "supervisor/images"
_DEFAULT_VIDEO_DIR = "supervisor/videos"

# 视频生成超时硬上限：Seedance 单条视频通常要 20 分钟左右才出片，所以这里就按
# 20 分钟兜底；超过即放弃，避免 supervisor 卡死等单个工具。
_VIDEO_TOOL_TIMEOUT_SECONDS = 1200.0

# 受支持的图像模型（其它值会落 IMAGE_MODEL_NOT_AVAILABLE）
_SUPPORTED_IMAGE_MODELS = {
    "gemini-3-pro-image-preview",
    "gemini-3.1-flash-image-preview",
}


@register_tool(
    name="generate_image",
    description=(
        "图像生成。**两种模式自动切换**：\n"
        "  - 图生图（image-to-image，**保人物/场景一致性的唯一办法**）：``asset_codes`` 传 1-5 个已有 asset_code（如 character.three_view_asset_code）→ 工具按 code 在 assets 表查图、做 i2i\n"
        "  - 文字驱动（text-to-image）：``asset_codes`` 不传 / 空 → 纯 prompt 出图。仅用于『首张基础图』（角色三视图 / 场景首图）\n\n"
        "**Agent 永远只看 asset_code，不看 URL**。出图成功后工具自动把新图保存到 ``assets`` 表并**自动分配 asset_code**（``img-<uuid>``），通过返回值给你。把返回的 code 写进 JSON / 后续 i2i 调用即可。\n\n"
        "Args:\n"
        "  prompt: 中文图像提示词\n"
        "  asset_codes: 参考图 asset_code 列表，最多 5 个。**传了就走 i2i**\n"
        "  description: 给新 asset 的人话描述（如 '萧炎三视图基础锚'）\n"
        "  tags: 新 asset 的 tags（如 ['character', '萧炎', 'three_view']）\n"
        "  negative_prompt: 负面提示词\n"
        "  aspect_ratio: '16:9' / '9:16' / '1:1' / '3:4' / '4:3'，默认 '16:9'\n"
        "  image_size: '512' / '1K' / '2K' / '4K'，默认 '1K'\n"
        "  model: 'gemini-3-pro-image-preview'（默认）/ 'gemini-3.1-flash-image-preview'\n"
        "Returns:\n"
        "  {success: True, asset_code: <自动分配的 code>, asset_id, mode: 'text2image'|'image2image', model, ...}；失败返回 tool_error。"
    ),
)
async def generate_image(
    prompt: str,
    asset_codes: Optional[list[str]] = None,
    description: Optional[str] = None,
    tags: Optional[list[str]] = None,
    negative_prompt: Optional[str] = None,
    aspect_ratio: str = "16:9",
    image_size: str = "1K",
    model: str = "gemini-3-pro-image-preview",
    oss_directory: str = _DEFAULT_IMAGE_DIR,
    *,
    memory_harness: Optional[Any] = None,
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

    project_id = _resolve_project_id(memory_harness)
    if project_id is None:
        return tool_error(
            error_code="PROJECT_ID_MISSING",
            message="无法解析 project_id —— memory_harness 未挂载或 scope_metadata 缺 domain_id",
            hint="确保 supervisor / sub-agent 是带 memory 启动的（memory_enabled=True 且 domain_id 已注入）",
        )

    from app.utils.image_gen import image_gen_client
    from app.utils.oss import oss_client

    # 运行时防御：LLM 有时会把 list 参数误传成单 string（"img-abc"）或 JSON 字符串
    # （'["a","b"]'）；Python 把 string 当 Iterable 会迭代成单字符序列。统一归一化
    ref_codes = _normalize_str_list(asset_codes)
    if ref_codes is _BAD_TYPE_SENTINEL:
        return tool_error(
            error_code="ASSET_CODES_BAD_TYPE",
            message=f"asset_codes 必须是 string 数组，收到 {type(asset_codes).__name__}: {asset_codes!r}",
            hint="i2i 时传一个 list 即可，如 asset_codes=['img-abc123']",
        )
    mode = "image2image" if ref_codes else "text2image"
    normalized_tags = _normalize_str_list(tags)
    if normalized_tags is _BAD_TYPE_SENTINEL:
        normalized_tags = []  # tags 是辅助元数据，不为它失败，宽容处理

    # 1) i2i 需要先按 code 把参考图字节拉下来
    ref_bytes: list[bytes] = []
    if mode == "image2image":
        try:
            ref_bytes, missing_codes = await _fetch_assets_bytes_by_code(
                project_id=project_id, codes=ref_codes
            )
        except Exception as exc:
            logger.exception("[media_tools] 拉取参考 asset 异常")
            return tool_error(
                error_code="REFERENCE_FETCH_EXCEPTION",
                message=f"拉取参考 asset 异常：{exc}",
                context={"asset_codes": ref_codes},
            )
        if not ref_bytes:
            return tool_error(
                error_code="REFERENCE_ASSETS_NOT_FOUND",
                message=f"asset_codes {ref_codes} 在 project_id={project_id} 下都查不到 / 拉不到字节",
                hint="检查 code 是否正确；或先用 t2i 出基础图（不传 asset_codes）再用其 code 做 i2i",
                context={"asset_codes": ref_codes, "missing": missing_codes},
            )

    # 2) 调模型出图
    try:
        if mode == "image2image":
            result = await image_gen_client.generate_with_reference(
                prompt=prompt,
                reference_images=ref_bytes,
                negative_prompt=negative_prompt,
                aspect_ratio=aspect_ratio,
                image_size=image_size,
                model=model,
            )
        else:
            result = await image_gen_client.generate(
                prompt=prompt,
                negative_prompt=negative_prompt,
                aspect_ratio=aspect_ratio,
                image_size=image_size,
                model=model,
            )
    except Exception as exc:
        logger.exception("[media_tools] image_gen 调用异常 model=%s mode=%s", model, mode)
        return tool_error(
            error_code="IMAGE_GEN_EXCEPTION",
            message=f"图像生成调用异常：{exc}",
            hint="检查 GOOGLE_API_KEY 配置或重试；持续失败可换 flash 模型",
            context={"model": model, "mode": mode},
        )

    if not result.success or not result.image_data:
        return tool_error(
            error_code="IMAGE_GEN_FAILED",
            message=result.error_message or "图像生成失败但模型未返回原因",
            hint="尝试调整 prompt（更具体 / 移除敏感词）后重试",
            context={"model": model, "rai_reason": result.rai_reason, "mode": mode},
        )

    # 3) 落 OSS
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

    # 4) 落 Asset 表，自动分配 asset_code
    try:
        final_code, asset_id = await _save_image_asset(
            project_id=project_id,
            file_url=url,
            file_format=suffix,
            file_size_bytes=len(result.image_data),
            generator=model,
            description=description,
            tags=normalized_tags,
        )
    except Exception as exc:
        logger.exception("[media_tools] 保存 asset 异常")
        return tool_error(
            error_code="ASSET_SAVE_FAILED",
            message=f"图已落 OSS 但 Asset 表写入失败：{exc}",
            hint="基础设施异常；URL 已生成（见 context）但不会被未来 i2i 引用到",
            context={"orphan_url": url},
        )

    return {
        "success": True,
        "asset_code": final_code,
        "asset_id": asset_id,
        "mode": mode,
        "model": model,
        "mime_type": result.mime_type,
        "aspect_ratio": aspect_ratio,
        "image_size": image_size,
    }


# ----------------------------------------------------------------------
# generate_image 内部 helpers
# ----------------------------------------------------------------------


_BAD_TYPE_SENTINEL: Any = object()


def _normalize_str_list(value: Any) -> Any:
    """把 LLM 传进来的 list[str] 参数归一化。

    宽容处理 LLM 常见错传：
    - ``None`` / ``[]`` → ``[]``
    - 单 string ``"img-abc"`` → ``["img-abc"]``
    - JSON 字符串 ``'["a","b"]'`` → ``["a","b"]``
    - 正常 ``list[str]`` → 过滤空串后返回

    其它非法类型（int / dict / list[dict] 等）返回 ``_BAD_TYPE_SENTINEL``——
    caller 据此决定报错还是宽容降级（如 tags 用 []）。
    """
    import json

    if value is None:
        return []
    if isinstance(value, str):
        s = value.strip()
        if not s:
            return []
        # 看是否是 JSON-encoded array
        if s.startswith("["):
            try:
                parsed = json.loads(s)
                if isinstance(parsed, list):
                    return [
                        item.strip() for item in parsed
                        if isinstance(item, str) and item.strip()
                    ]
            except json.JSONDecodeError:
                pass
        return [s]
    if isinstance(value, list):
        return [item.strip() for item in value if isinstance(item, str) and item.strip()]
    return _BAD_TYPE_SENTINEL


def _resolve_project_id(memory_harness: Any) -> Optional[int]:
    """从 memory_harness 拿 project_id（FilmGenX 把 project.id 当 domain_id 注入）。"""
    if memory_harness is None:
        return None
    scope = getattr(getattr(memory_harness, "config", None), "scope_metadata", None) or {}
    domain_id = scope.get("domain_id")
    if isinstance(domain_id, int) and domain_id > 0:
        return domain_id
    if isinstance(domain_id, str) and domain_id.isdigit():
        return int(domain_id)
    return None


async def _fetch_assets_bytes_by_code(
    *, project_id: int, codes: list[str]
) -> tuple[list[bytes], list[str]]:
    """按 asset_code 查 assets 表，拉每张图的字节。

    返回 ``(bytes_list, missing_codes)``：bytes 顺序按 ``codes`` 输入；查不到 / 拉不到的
    code 进 missing_codes，但不影响其它图继续走。
    """
    from app.db.session import AsyncSessionFactory
    from app.models.asset import Asset
    from sqlalchemy import select
    import httpx

    async with AsyncSessionFactory() as session:
        stmt = select(Asset).where(
            Asset.project_id == project_id,
            Asset.asset_code.in_(codes),
            Asset.is_deleted.is_(False),
        )
        rows = (await session.execute(stmt)).scalars().all()

    by_code = {row.asset_code: row for row in rows}

    bytes_list: list[bytes] = []
    missing: list[str] = []
    async with httpx.AsyncClient(timeout=20.0) as client:
        for code in codes:
            asset = by_code.get(code)
            if asset is None:
                missing.append(code)
                continue
            try:
                resp = await client.get(asset.file_url)
                resp.raise_for_status()
                bytes_list.append(resp.content)
            except Exception as exc:
                logger.warning(
                    "[media_tools] 拉取 asset_code=%s url=%s 失败：%s",
                    code, asset.file_url, exc,
                )
                missing.append(code)

    return bytes_list, missing


async def _save_image_asset(
    *,
    project_id: int,
    file_url: str,
    file_format: str,
    file_size_bytes: int,
    generator: str,
    description: Optional[str],
    tags: list[str],
) -> tuple[str, int]:
    """把生成的图插入 assets 表，自动分配 ``img-<uuid_short>`` 作为 asset_code，返回 (code, id)。"""
    from uuid import uuid4

    from app.db.session import AsyncSessionFactory
    from app.models.asset import Asset

    code = f"img-{uuid4().hex[:10]}"

    async with AsyncSessionFactory() as session:
        async with session.begin():
            row = Asset(
                project_id=project_id,
                asset_code=code,
                asset_type="image",
                file_url=file_url,
                file_format=file_format,
                file_size_bytes=file_size_bytes,
                source="generated",
                generator=generator,
                description=description,
                tags=tags,
            )
            session.add(row)
            await session.flush()
            new_id = row.id

    return code, new_id


@register_tool(
    name="generate_video",
    description=(
        "视频生成（Seedance 2.0 reference-to-video）。基于参考素材出片，产物自动落 OSS "
        "并写入 ``assets`` 表，自动分配 ``vid-<uuid>`` 作为 asset_code。\n\n"
        "**Agent 永远只看 asset_code，不看 URL**。把返回的 code 写进 JSON / 后续 i2v 调用即可。\n\n"
        "Args:\n"
        "  prompt:         中文运动 prompt（运镜 + 角色动作 + 节奏；≤500 字符）\n"
        "  asset_codes:    参考素材 asset_code 列表（最多 9 个，必填）。**至少要传一项**——\n"
        "                  Seedance reference-to-video 不支持纯文生视频。prompt 里用\n"
        "                  '参考图 1' / 'reference image 2' 这种自然语言指代各路素材的用途。\n"
        "  duration:       时长秒，4-15，默认 5\n"
        "  aspect_ratio:   '16:9' / '9:16' / '1:1' / '4:3' / '3:4' / '21:9' / 'adaptive'，默认 '16:9'\n"
        "  generate_audio: 是否生成同步音频，默认 True\n"
        "  description:    给新视频 asset 的人话描述（如 '萧炎冲入云海·第一幕镜头 3'）\n"
        "  tags:           新 asset 的 tags（如 ['video', 'shot_3', '萧炎']）\n"
        "Returns:\n"
        "  {success: True, asset_code: <自动分配的 vid-xxx>, asset_id, url, task_id, "
        "duration, aspect_ratio, generate_audio}；失败返回 tool_error。\n"
        "Note: Seedance 单条视频通常 20 分钟左右出片，工具内部硬限制 20 分钟超时。"
    ),
)
async def generate_video(
    prompt: str,
    asset_codes: Optional[list[str]] = None,
    duration: int = 5,
    aspect_ratio: str = "16:9",
    generate_audio: bool = True,
    description: Optional[str] = None,
    tags: Optional[list[str]] = None,
    *,
    memory_harness: Optional[Any] = None,
) -> Dict[str, Any]:
    project_id = _resolve_project_id(memory_harness)
    if project_id is None:
        return tool_error(
            error_code="PROJECT_ID_MISSING",
            message="无法解析 project_id —— memory_harness 未挂载或 scope_metadata 缺 domain_id",
            hint="确保 supervisor / sub-agent 是带 memory 启动的（memory_enabled=True 且 domain_id 已注入）",
        )

    ref_codes = _normalize_str_list(asset_codes)
    if ref_codes is _BAD_TYPE_SENTINEL:
        return tool_error(
            error_code="ASSET_CODES_BAD_TYPE",
            message=f"asset_codes 必须是 string 数组，收到 {type(asset_codes).__name__}: {asset_codes!r}",
            hint="例如 asset_codes=['img-abc123', 'img-def456']",
        )
    if not ref_codes:
        return tool_error(
            error_code="ASSET_CODES_REQUIRED",
            message="Seedance reference-to-video 不支持纯文生视频，必须至少传一个 asset_code",
            hint="先用 generate_image 出基础图（角色三视图 / 场景首图），再把它的 asset_code 作为参考传进来",
        )

    normalized_tags = _normalize_str_list(tags)
    if normalized_tags is _BAD_TYPE_SENTINEL:
        normalized_tags = []

    # asset_code → file_url
    try:
        ref_urls, missing_codes = await _resolve_asset_urls_by_code(
            project_id=project_id, codes=ref_codes
        )
    except Exception as exc:
        logger.exception("[media_tools] 解析参考 asset URL 异常")
        return tool_error(
            error_code="REFERENCE_FETCH_EXCEPTION",
            message=f"解析参考 asset 异常：{exc}",
            context={"asset_codes": ref_codes},
        )
    if not ref_urls:
        return tool_error(
            error_code="REFERENCE_ASSETS_NOT_FOUND",
            message=f"asset_codes {ref_codes} 在 project_id={project_id} 下都查不到",
            hint="检查 code 是否正确；或先用 generate_image 产出再用其 code",
            context={"asset_codes": ref_codes, "missing": missing_codes},
        )

    from app.utils.seedance import seedance_client

    # 整个视频生成 + OSS + 入库流程包在 20 分钟硬上限里。Seedance 内部
    # ``wait_for_completion`` 自己也有 max_wait_seconds=1200；这里再裹一层是防御
    # OSS 下载 / DB 写入卡死的极端场景，让 supervisor 不会被单个 tool call 拖死。
    try:
        return await asyncio.wait_for(
            _run_seedance_image_to_video(
                seedance_client=seedance_client,
                project_id=project_id,
                prompt=prompt,
                image_urls=ref_urls,
                duration=duration,
                aspect_ratio=aspect_ratio,
                generate_audio=generate_audio,
                description=description,
                tags=normalized_tags,
                ref_codes=ref_codes,
            ),
            timeout=_VIDEO_TOOL_TIMEOUT_SECONDS,
        )
    except asyncio.TimeoutError:
        return tool_error(
            error_code="VIDEO_TOOL_TIMEOUT",
            message=f"视频生成超过 {_VIDEO_TOOL_TIMEOUT_SECONDS:.0f}s 仍未完成",
            hint="可能是 Seedance 端排队或 OSS 上传卡住；稍后重试，或减短 duration",
        )


async def _run_seedance_image_to_video(
    *,
    seedance_client: Any,
    project_id: int,
    prompt: str,
    image_urls: list[str],
    duration: int,
    aspect_ratio: str,
    generate_audio: bool,
    description: Optional[str],
    tags: list[str],
    ref_codes: list[str],
) -> Dict[str, Any]:
    """generate_video 主流程的实际执行体。从 ``generate_video`` 拆出来是为了让外层
    用 ``asyncio.wait_for`` 整体加超时；超时分支可以干净地杀掉整个流程而不留
    halfway state。
    """
    # 1) 提交 Seedance 任务
    try:
        task = await seedance_client.image_to_video(
            prompt=prompt,
            image_urls=image_urls,
            duration=duration,
            aspect_ratio=aspect_ratio,
            generate_audio=generate_audio,
        )
    except ValueError as exc:
        # 入参校验失败（quality / aspect_ratio / duration 越界等）
        return tool_error(
            error_code="VIDEO_PARAMS_INVALID",
            message=f"Seedance 入参不合法：{exc}",
            hint="检查 duration（4-15）/ aspect_ratio 等是否在允许范围",
        )
    except Exception as exc:
        logger.exception("[media_tools] seedance image_to_video 提交异常")
        return tool_error(
            error_code="VIDEO_SUBMIT_FAILED",
            message=f"Seedance 任务提交失败：{exc}",
            hint="检查 prompt 是否合规 / 参考图是否可下载，或稍后重试",
        )

    # 2) 轮询完成 + OSS 上传（拿永久 URL，Seedance 自带链接 24h 失效）
    try:
        finished = await seedance_client.wait_for_completion(
            task.id,
            upload_to_oss=True,
            oss_directory=_DEFAULT_VIDEO_DIR,
        )
    except TimeoutError as exc:
        return tool_error(
            error_code="VIDEO_GEN_TIMEOUT",
            message=str(exc),
            hint="Seedance 服务端可能在排队；稍后用同样参数重试",
            context={"task_id": task.id},
        )
    except Exception as exc:
        logger.exception("[media_tools] seedance 任务等待异常 task_id=%s", task.id)
        return tool_error(
            error_code="VIDEO_GEN_FAILED",
            message=f"Seedance 任务执行失败：{exc}",
            hint="检查任务详情或调整 prompt 后重试",
            context={"task_id": task.id},
        )

    if finished.status != "completed" or not finished.video_url:
        return tool_error(
            error_code="VIDEO_GEN_FAILED",
            message=f"Seedance 任务结束但未拿到视频 URL（status={finished.status}）",
            context={"task_id": finished.id, "status": finished.status},
        )

    # 3) 落 Asset 表，自动分配 vid-<uuid> code
    final_duration = finished.video_duration or float(duration)
    try:
        final_code, asset_id = await _save_video_asset(
            project_id=project_id,
            file_url=finished.video_url,
            duration_sec=final_duration,
            aspect_ratio=aspect_ratio,
            generator="seedance-2.0-reference-to-video",
            description=description,
            tags=tags,
        )
    except Exception as exc:
        logger.exception("[media_tools] 保存视频 asset 异常")
        return tool_error(
            error_code="ASSET_SAVE_FAILED",
            message=f"视频已生成并落 OSS 但 Asset 表写入失败：{exc}",
            hint="基础设施异常；URL 已生成（见 context）但不会被未来 i2v 引用到",
            context={"orphan_url": finished.video_url, "task_id": finished.id},
        )

    return {
        "success": True,
        "asset_code": final_code,
        "asset_id": asset_id,
        "url": finished.video_url,
        "task_id": finished.id,
        "duration": final_duration,
        "aspect_ratio": aspect_ratio,
        "generate_audio": generate_audio,
        "model": "seedance-2.0-reference-to-video",
        "reference_codes": ref_codes,
    }


async def _resolve_asset_urls_by_code(
    *, project_id: int, codes: list[str]
) -> tuple[list[str], list[str]]:
    """按 ``asset_code`` 在 assets 表查 ``file_url``。

    返回 ``(urls, missing_codes)``；urls 顺序按输入 codes，查不到的进 missing。
    Seedance 接受的是 URL（参考图通过 https 让对端下载），所以这里只取 URL 而不像
    image i2i 那样把字节拉下来。
    """
    from app.db.session import AsyncSessionFactory
    from app.models.asset import Asset
    from sqlalchemy import select

    async with AsyncSessionFactory() as session:
        stmt = select(Asset).where(
            Asset.project_id == project_id,
            Asset.asset_code.in_(codes),
            Asset.is_deleted.is_(False),
        )
        rows = (await session.execute(stmt)).scalars().all()

    by_code = {row.asset_code: row for row in rows}

    urls: list[str] = []
    missing: list[str] = []
    for code in codes:
        asset = by_code.get(code)
        if asset is None or not asset.file_url:
            missing.append(code)
            continue
        urls.append(asset.file_url)

    return urls, missing


async def _save_video_asset(
    *,
    project_id: int,
    file_url: str,
    duration_sec: float,
    aspect_ratio: str,
    generator: str,
    description: Optional[str],
    tags: list[str],
) -> tuple[str, int]:
    """把生成的视频插入 assets 表，自动分配 ``vid-<uuid_short>`` 为 asset_code。"""
    from uuid import uuid4

    from app.db.session import AsyncSessionFactory
    from app.models.asset import Asset

    code = f"vid-{uuid4().hex[:10]}"

    async with AsyncSessionFactory() as session:
        async with session.begin():
            row = Asset(
                project_id=project_id,
                asset_code=code,
                asset_type="video",
                file_url=file_url,
                file_format="mp4",
                duration_sec=duration_sec,
                source="generated",
                generator=generator,
                description=description,
                tags=[*tags, f"aspect_ratio:{aspect_ratio}"],
            )
            session.add(row)
            await session.flush()
            new_id = row.id

    return code, new_id
