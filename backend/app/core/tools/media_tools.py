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
import re
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
        "  name: **必填**——人类可读名字，用于前端卡片标题 + 下游 generate_video 自动桥接 Seedance prompt 别名。\n"
        "    示例：角色三视图填 '萧炎'；场景图填 '云岚宗广场'；表情变体填 '萧炎-愤怒'；"
        "测试图至少给个描述性标签如 '夜景街道-测试'。**不能省略**，留空会让前端展示退回到 asset_code（一串 hex）。\n"
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
    name: str,
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
            name=name,
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
# generate_image_evolink —— GPT-Image-2 测试工具
#
# 与 generate_image 并行注册，方便 workspace agent A/B 对比：
#   - generate_image:        Gemini 原生（直接拿 image bytes，同步）
#   - generate_image_evolink: Evolink GPT-Image-2（异步任务，URL 返回 + 24h 失效）
#
# 与 generate_image 的核心差异：
#   1. 模型：gpt-image-2（vs gemini-3-pro-image-preview / flash）
#   2. i2i 入参形态：传 URL（vs Gemini 拿 bytes 再喂模型）
#   3. 支持 n>1：单次出多张图供挑选
#   4. quality / resolution 显式分档（low/medium/high × 1K/2K/4K）
# ----------------------------------------------------------------------

_EVOLINK_IMAGE_TIMEOUT_SECONDS = 600.0  # GPT-Image-2 实测有时排队较久，10 分钟兜底
_EVOLINK_IMAGE_MAX_N = 5  # 工具内部限制：测试场景超过 5 张意义不大且费配额


@register_tool(
    name="generate_image_evolink",
    description=(
        "图像生成（Evolink GPT-Image-2，**测试工具**，与 generate_image 并行）。"
        "**两种模式自动切换**：\n"
        "  - 图生图（image-to-image）：``asset_codes`` 传 1-16 个已有 asset_code → 工具解析为 URL "
        "传给 Evolink；提示词里指明编辑意图（如 '把场景改成雨夜，加一把伞'）\n"
        "  - 文生图（text-to-image）：``asset_codes`` 不传 / 空 → 纯 prompt 出图\n\n"
        "**Agent 永远只看 asset_code，不看 URL**。出图成功后工具自动把每张新图保存到 ``assets`` 表"
        "并**自动分配 asset_code**（``img-<uuid>``），通过返回值给你。\n\n"
        "Args:\n"
        "  prompt: 中文或英文图像提示词，≤32000 字符\n"
        "  name: **必填**——人类可读名字（如 '萧炎'、'云岚宗广场'、'夜景街道-测试'）。"
        "前端用它做卡片标题，下游 generate_video 用它做 Seedance prompt 别名桥接。"
        "n>1 时所有新 asset 共用同一个 name（每张自动加 -1 / -2 后缀避免重名）。**不能省略**。\n"
        "  asset_codes: 参考图 asset_code 列表，最多 16 个。**传了就走 i2i**\n"
        "  description: 给新 asset 的人话描述（n>1 时所有新 asset 共用）\n"
        "  tags: 新 asset 的 tags\n"
        "  aspect_ratio: '1:1' / '16:9' / '9:16' / '4:3' / '3:4' 或像素 '1024x1024'，默认 '1:1'\n"
        "  resolution: '1K'（默认）/ '2K' / '4K'\n"
        "  quality: 'low' / 'medium'（默认）/ 'high'\n"
        "  n: 生成张数，1-5，默认 1\n"
        "Returns:\n"
        "  {success: True, asset_code, asset_codes, asset_id, asset_ids, url, urls, "
        "mode: 'text2image'|'image2image', model: 'gpt-image-2', task_id, ...}；"
        "失败返回 tool_error。\n"
        "Note: 内部 10 分钟硬超时（Evolink GPT-Image-2 排队情况下偶尔会拖长）。"
    ),
)
async def generate_image_evolink(
    prompt: str,
    name: str,
    asset_codes: Optional[list[str]] = None,
    description: Optional[str] = None,
    tags: Optional[list[str]] = None,
    aspect_ratio: str = "1:1",
    resolution: str = "1K",
    quality: str = "medium",
    n: int = 1,
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

    if not (1 <= n <= _EVOLINK_IMAGE_MAX_N):
        return tool_error(
            error_code="N_OUT_OF_RANGE",
            message=f"n 必须在 1-{_EVOLINK_IMAGE_MAX_N}（当前 {n}）",
            hint="测试用工具，单次最多 5 张避免烧配额",
        )

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
        normalized_tags = []

    # 1) i2i 解析 asset_code → URL（Evolink 直接消费 URL，不需要拉字节）
    ref_urls: list[str] = []
    if mode == "image2image":
        try:
            ref_urls, missing_codes = await _resolve_asset_urls_by_code(
                project_id=project_id, codes=ref_codes
            )
        except Exception as exc:
            logger.exception("[media_tools] evolink: 解析参考 asset URL 异常")
            return tool_error(
                error_code="REFERENCE_FETCH_EXCEPTION",
                message=f"解析参考 asset 异常：{exc}",
                context={"asset_codes": ref_codes},
            )
        if not ref_urls:
            return tool_error(
                error_code="REFERENCE_ASSETS_NOT_FOUND",
                message=f"asset_codes {ref_codes} 在 project_id={project_id} 下都查不到",
                hint="检查 code 是否正确；或先用 t2i 出基础图（不传 asset_codes）再用其 code",
                context={"asset_codes": ref_codes, "missing": missing_codes},
            )

    # 2) 包整个流程在 10 分钟硬上限里
    try:
        return await asyncio.wait_for(
            _run_evolink_image_generation(
                project_id=project_id,
                prompt=prompt,
                ref_urls=ref_urls or None,
                aspect_ratio=aspect_ratio,
                resolution=resolution,
                quality=quality,
                n=n,
                mode=mode,
                ref_codes=ref_codes,
                description=description,
                tags=normalized_tags,
                name=name,
            ),
            timeout=_EVOLINK_IMAGE_TIMEOUT_SECONDS,
        )
    except asyncio.TimeoutError:
        return tool_error(
            error_code="IMAGE_TOOL_TIMEOUT",
            message=f"图像生成超过 {_EVOLINK_IMAGE_TIMEOUT_SECONDS:.0f}s 仍未完成",
            hint="可能 Evolink 排队或 OSS 上传卡住；稍后重试",
        )


async def _run_evolink_image_generation(
    *,
    project_id: int,
    prompt: str,
    ref_urls: Optional[list[str]],
    aspect_ratio: str,
    resolution: str,
    quality: str,
    n: int,
    mode: str,
    ref_codes: list[str],
    description: Optional[str],
    tags: list[str],
    name: Optional[str] = None,
) -> Dict[str, Any]:
    """generate_image_evolink 主流程，拆出来配合 asyncio.wait_for 总超时。"""
    from app.utils.evolink import evolink_client

    # 1) 提交 Evolink 任务
    try:
        task = await evolink_client.image_generation(
            prompt=prompt,
            image_urls=ref_urls,
            size=aspect_ratio,
            resolution=resolution,
            quality=quality,
            n=n,
        )
    except ValueError as exc:
        # 入参越界 / 不合法
        return tool_error(
            error_code="IMAGE_PARAMS_INVALID",
            message=f"Evolink 入参不合法：{exc}",
            hint="检查 aspect_ratio / resolution / quality / n 是否在允许范围",
        )
    except Exception as exc:
        logger.exception("[media_tools] evolink image_generation 提交异常 mode=%s", mode)
        return tool_error(
            error_code="IMAGE_SUBMIT_FAILED",
            message=f"Evolink 任务提交失败：{exc}",
            hint="检查 EVOLINK_API_KEY 或稍后重试",
        )

    # 2) 轮询完成 + OSS 上传（拿永久 URL，Evolink 链接 24h 失效）
    try:
        finished = await evolink_client.wait_for_completion(
            task.id,
            poll_interval=3.0,
            upload_to_oss=True,
            oss_directory=_DEFAULT_IMAGE_DIR,
        )
    except TimeoutError as exc:
        return tool_error(
            error_code="IMAGE_GEN_TIMEOUT",
            message=str(exc),
            hint="Evolink 服务端排队；稍后重试",
            context={"task_id": task.id},
        )
    except Exception as exc:
        logger.exception("[media_tools] evolink 任务等待异常 task_id=%s", task.id)
        return tool_error(
            error_code="IMAGE_GEN_FAILED",
            message=f"Evolink 任务执行失败：{exc}",
            hint="检查任务详情或调整 prompt 后重试",
            context={"task_id": task.id},
        )

    if finished.status != "completed" or not finished.results:
        return tool_error(
            error_code="IMAGE_GEN_FAILED",
            message=f"Evolink 任务结束但未拿到图片 URL（status={finished.status}）",
            context={"task_id": finished.id, "status": finished.status},
        )

    # 3) 落 Asset 表（n 张分别落 + 分配 vid-style img-<uuid> 句柄）
    saved_codes: list[str] = []
    saved_ids: list[int] = []
    try:
        n_results = len(finished.results)
        for idx, url in enumerate(finished.results, start=1):
            # n>1 时给每张 name 加 -1 / -2 后缀避免重名（"萧炎" → "萧炎-1"、"萧炎-2"）
            row_name: Optional[str] = None
            if name:
                row_name = f"{name}-{idx}" if n_results > 1 else name
            code, asset_id = await _save_image_asset(
                project_id=project_id,
                file_url=url,
                file_format="png",  # GPT-Image-2 默认 PNG
                file_size_bytes=None,
                generator="gpt-image-2",
                description=description,
                tags=[*tags, f"evolink", f"mode:{mode}"],
                name=row_name,
            )
            saved_codes.append(code)
            saved_ids.append(asset_id)
    except Exception as exc:
        logger.exception("[media_tools] evolink: 保存 asset 异常")
        return tool_error(
            error_code="ASSET_SAVE_FAILED",
            message=f"图已落 OSS 但 Asset 表写入失败：{exc}",
            hint="基础设施异常；OSS URL 已生成但不会被未来 i2i 引用到",
            context={"orphan_urls": finished.results, "task_id": finished.id},
        )

    # 4) 返回，n=1 时 asset_code/asset_id/url 是单值（最常用），同时也给 plural 字段
    return {
        "success": True,
        "asset_code": saved_codes[0],
        "asset_codes": saved_codes,
        "asset_id": saved_ids[0],
        "asset_ids": saved_ids,
        "url": finished.results[0],
        "urls": finished.results,
        "mode": mode,
        "model": "gpt-image-2",
        "task_id": finished.id,
        "aspect_ratio": aspect_ratio,
        "resolution": resolution,
        "quality": quality,
        "n": n,
        "reference_codes": ref_codes,
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
    file_size_bytes: Optional[int],
    generator: str,
    description: Optional[str],
    tags: list[str],
    name: Optional[str] = None,
) -> tuple[str, int]:
    """把生成的图插入 assets 表，自动分配 ``img-<uuid_short>`` 作为 asset_code，返回 (code, id)。

    ``file_size_bytes`` 可为 ``None``（如走 Evolink 异步任务，只拿到 URL 不拉字节时）。
    ``name`` 是人类可读的名字（"萧炎"、"云岚宗广场"），前端展示 + Seedance prompt 别名注入会用。
    """
    from uuid import uuid4

    from app.db.session import AsyncSessionFactory
    from app.models.asset import Asset

    code = f"img-{uuid4().hex[:10]}"

    async with AsyncSessionFactory() as session:
        async with session.begin():
            row = Asset(
                project_id=project_id,
                asset_code=code,
                name=name,
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
        "  prompt:         中文运动 prompt（运镜 + 角色动作 + 节奏；≤500 字符）。\n"
        "                  **可在 prompt 里用 Seedance 官方引用语法精确指代参考图**：\n"
        "                    ``@图片1`` / ``@图片2`` / ... ``@图片9``\n"
        "                  编号按 ``asset_codes`` 列表顺序，1-indexed。例如\n"
        "                  ``asset_codes=['img-char', 'img-scene']`` 时，prompt 写\n"
        "                  ``@图片1 持剑奔向 @图片2 中的悬崖``。\n"
        "  name:           **必填**——给生成的视频 asset 起个人话名字（如 '萧炎冲入云海·镜头 3'、"
        "'测试运镜-推拉摇'）。前端用它做卡片标题。**不能省略**。\n"
        "  asset_codes:    参考素材 asset_code 列表（最多 9 个，必填）。**至少要传一项**——\n"
        "                  Seedance reference-to-video 不支持纯文生视频。\n"
        "  duration:       时长秒，4-15，默认 5\n"
        "  aspect_ratio:   '16:9' / '9:16' / '1:1' / '4:3' / '3:4' / '21:9' / 'adaptive'，默认 '16:9'\n"
        "  generate_audio: 是否生成同步音频，默认 True\n"
        "  description:    给新视频 asset 的人话描述（更长一些的说明）\n"
        "  tags:           新 asset 的 tags（如 ['video', 'shot_3', '萧炎']）\n"
        "Returns:\n"
        "  {success: True, asset_code: <自动分配的 vid-xxx>, asset_id, url, task_id, "
        "duration, aspect_ratio, generate_audio, image_refs, name_refs}；失败返回 tool_error。\n"
        "  ``image_refs`` 是 ``{'@图片1': 'img-xxx', '@图片2': 'img-yyy'}`` 的映射，方便你复核。\n"
        "  ``name_refs`` 是从 ``assets.name`` 反查到的别名映射，如 ``{'萧炎': '@图片1', '云岚宗广场': '@图片2'}``；\n"
        "  工具会**自动**在 prompt 头部前置一行 ``素材引用：萧炎=@图片1，云岚宗广场=@图片2``，\n"
        "  让 Seedance 看到 prompt 正文里的中文名时就知道对应哪张图。\n"
        "  所以你写 prompt 时可以直接用中文名（如 '萧炎冲向云岚宗广场'），不需要手动嵌 @图片N，\n"
        "  工具帮你做名字到图片编号的桥接。当然显式 @图片N 也支持（两种可以混用）。\n"
        "Note: Seedance 单条视频通常 20 分钟左右出片，工具内部硬限制 20 分钟超时。"
    ),
)
async def generate_video(
    prompt: str,
    name: str,
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
                name=name,
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
    name: Optional[str] = None,
) -> Dict[str, Any]:
    """generate_video 主流程的实际执行体。从 ``generate_video`` 拆出来是为了让外层
    用 ``asyncio.wait_for`` 整体加超时；超时分支可以干净地杀掉整个流程而不留
    halfway state。
    """
    # 0) 计算 @图片N → asset_code 映射（按 image_urls 顺序，1-indexed）
    #    Seedance 官方约定 prompt 里用 ``@图片1`` / ``@图片2`` ... 来精确引用参考图，
    #    比如 "@图片1 站在 @图片2 描述的场景中央"。这里：
    #    - 提前校验 prompt 里所有 @图片N 编号都在 1..len(ref_codes) 之内，越界直接 fail-fast
    #    - 把映射打日志 + 回传给 agent，方便复核 Seedance 看到的是哪几张图对哪个序号
    image_refs: Dict[str, str] = {
        f"@图片{i + 1}": code for i, code in enumerate(ref_codes)
    }
    ref_validation_error = _validate_seedance_image_refs(prompt, len(ref_codes))
    if ref_validation_error is not None:
        return ref_validation_error
    if image_refs:
        logger.info(
            "[media_tools] seedance image_refs (按 asset_codes 顺序映射): %s",
            image_refs,
        )

    # 0.5) 直接从 assets 表反查每个 asset_code 的 ``name`` 字段，用于在 prompt 头部
    #      注入 "萧炎=@图片1, 云岚宗广场=@图片2" 这样的别名表，让 Seedance 在 prompt
    #      正文里看到中文名时就知道对应哪张图。``name`` 是 assets 表的人话标签
    #      （由上游 generate_image / character_ref_agent 等填入），所以这里只是
    #      普通 SELECT，不再依赖 memory KV 反查。
    name_refs: Dict[str, str] = {}
    if ref_codes:
        try:
            code_to_name = await _lookup_asset_names_by_code(
                project_id=project_id, codes=ref_codes
            )
        except Exception as exc:  # noqa: BLE001
            # 反查失败不阻塞主流程——agent 仍可走 @图片N 模式
            logger.warning(
                "[media_tools] 反查 asset_code → asset.name 异常（继续，不注入别名表）：%s",
                exc,
            )
            code_to_name = {}
        for i, code in enumerate(ref_codes):
            ent_name = code_to_name.get(code)
            if ent_name:
                name_refs[ent_name] = f"@图片{i + 1}"

    # 0.6) 把别名表前置到 prompt（仅在反查到至少一个名字时）
    augmented_prompt = prompt
    if name_refs:
        alias_line = "，".join(f"{n}={ref}" for n, ref in name_refs.items())
        augmented_prompt = f"素材引用：{alias_line}\n\n{prompt}"
        logger.info(
            "[media_tools] seedance prompt 前置素材引用别名：%s",
            alias_line,
        )

    # 1) 提交 Seedance 任务
    try:
        task = await seedance_client.image_to_video(
            prompt=augmented_prompt,
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
            name=name,
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
        # 1-indexed 映射：prompt 里 ``@图片N`` 对应哪个 asset_code，方便 agent 自查
        "image_refs": image_refs,
        # 反查到的"实体名 → @图片N"映射（character / scene 名），prompt 头部已自动前置
        "name_refs": name_refs,
    }


async def _lookup_asset_names_by_code(
    *,
    project_id: int,
    codes: list[str],
) -> Dict[str, str]:
    """从 assets 表反查每个 ``asset_code`` 对应的 ``name`` 字段。

    Returns:
        ``{asset_code: name}``；``name`` 为 NULL / 空字符串的 code 不进 dict。
    """
    from app.db.session import AsyncSessionFactory
    from app.models.asset import Asset
    from sqlalchemy import select

    if not codes:
        return {}

    async with AsyncSessionFactory() as session:
        stmt = select(Asset.asset_code, Asset.name).where(
            Asset.project_id == project_id,
            Asset.asset_code.in_(codes),
            Asset.is_deleted.is_(False),
        )
        rows = (await session.execute(stmt)).all()

    return {row[0]: row[1] for row in rows if row[1]}


# Seedance prompt 里 ``@图片N`` 的引用语法校验：N 必须是 1-indexed，且 ≤ len(ref_codes)
_SEEDANCE_IMAGE_REF_PATTERN = re.compile(r"@图片(\d+)")


def _validate_seedance_image_refs(
    prompt: str,
    ref_count: int,
) -> Optional[Dict[str, Any]]:
    """扫描 prompt 中所有 ``@图片N`` 引用，越界 / 编号为 0 时返回结构化错误。

    Returns:
        ``None`` 表示通过；命中错误时返回 ``tool_error(...)`` 字典直接给 caller。

    Note:
        Seedance 官方文档定义的命名是 ``@图片1`` ~ ``@图片9``（按 ``image_urls`` 顺序）。
        agent 写 ``@图片3`` 但只传了 2 张图 → 提前 fail-fast，错误信息明确告诉它哪个编号
        越界、应改成什么；比让 Seedance 端 422 信息更可读。
    """
    matches = _SEEDANCE_IMAGE_REF_PATTERN.findall(prompt)
    if not matches:
        return None

    # 去重保留出现顺序：用 dict 也行
    seen: list[int] = []
    for raw in matches:
        idx = int(raw)
        if idx not in seen:
            seen.append(idx)

    bad: list[int] = [idx for idx in seen if idx < 1 or idx > ref_count]
    if bad:
        return tool_error(
            error_code="VIDEO_PROMPT_REF_OUT_OF_RANGE",
            message=(
                f"prompt 引用了 @图片{bad}，但当前只传了 {ref_count} 张参考图"
                f"（合法编号 1-{ref_count}）"
            ),
            hint=(
                f"按 asset_codes 顺序索引：第 1 个 code 对应 @图片1，第 2 个对应 @图片2 ...；"
                "要引用更多图，先在 asset_codes 里把对应的 code 加进去；"
                "或者改 prompt 里的 @图片N 编号到合法范围"
            ),
            context={"out_of_range": bad, "ref_count": ref_count},
        )
    return None


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
    name: Optional[str] = None,
) -> tuple[str, int]:
    """把生成的视频插入 assets 表，自动分配 ``vid-<uuid_short>`` 为 asset_code。

    ``name`` 是人类可读的名字（"萧炎冲入云海·镜头 3"），前端展示用。
    """
    from uuid import uuid4

    from app.db.session import AsyncSessionFactory
    from app.models.asset import Asset

    code = f"vid-{uuid4().hex[:10]}"

    async with AsyncSessionFactory() as session:
        async with session.begin():
            row = Asset(
                project_id=project_id,
                asset_code=code,
                name=name,
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
