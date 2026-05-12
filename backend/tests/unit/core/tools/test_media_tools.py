"""
media_tools 工具薄包装回归（2 工具版：generate_image / generate_video）。

钉死：
- 注册表里只暴露 generate_image / generate_video 两个工具
- model 由参数传递（带默认值）；非法 model 走 *_MODEL_NOT_AVAILABLE 错误
- 成功路径：参数透传给 utils 客户端 + 拿到 OSS URL + 返回 success=True
- 失败路径：utils 失败 / 抛异常 / OSS 失败 → 返回 tool_error 形态（ok=False + error_code）
- generate_video model='seedance' 走 MODEL_NOT_AVAILABLE，**不**触发 evolink
"""

from __future__ import annotations

import pytest

# 触发 @register_tool 注册
from app.core.tools import media_tools as _media_tools  # noqa: F401
from app.core.tools.registry import ToolRegistry


MEDIA_TOOL_NAMES = ["generate_image", "generate_video"]
LEGACY_TOOL_NAMES = [
    "generate_image_pro",
    "generate_image_flash",
    "generate_video_text_to_video",
    "generate_video_image_to_video",
]


# --------------------------------------------------------------------- #
# 注册 + schema 形态
# --------------------------------------------------------------------- #


@pytest.mark.parametrize("name", MEDIA_TOOL_NAMES)
def test_media_tool_registered(name: str):
    tool = ToolRegistry.get(name)
    assert tool is not None, f"{name} 未注册到 ToolRegistry"
    schema = tool.get_schema()
    assert schema.get("name") == name
    desc = schema.get("description") or ""
    assert len(desc) > 30, f"{name} description 太短"


@pytest.mark.parametrize("name", LEGACY_TOOL_NAMES)
def test_legacy_tools_no_longer_registered(name: str):
    """4 个老工具已经收敛，不应该再出现在注册表里。"""
    assert ToolRegistry.get(name) is None, f"老工具 {name} 仍被注册"


# --------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------- #


class _FakeImageResult:
    def __init__(self, success: bool, image_data: bytes | None = None,
                 mime_type: str | None = "image/png", error_message: str | None = None,
                 rai_reason: str | None = None):
        self.success = success
        self.image_data = image_data
        self.mime_type = mime_type
        self.error_message = error_message
        self.rai_reason = rai_reason


class _FakeVideoTask:
    def __init__(self, *, id: str = "task-1", status: str = "completed",
                 video_url: str | None = "https://oss/video.mp4",
                 video_duration: float | None = 5.0):
        self.id = id
        self.status = status
        self.video_url = video_url
        self.video_duration = video_duration


class _FakeMemoryHarness:
    """最小 memory_harness mock：generate_image 只读 scope_metadata.domain_id 拿 project_id。"""

    def __init__(self, domain_id: int = 1):
        from types import SimpleNamespace
        self.config = SimpleNamespace(scope_metadata={"domain_id": domain_id})


def _patch_asset_save(monkeypatch, *, code: str = "img-test", asset_id: int = 1):
    """绕过 Asset 表写入：直接 mock 内部 helper 返 (code, id)。"""
    async def _fake_save(**kwargs):
        return (code, asset_id)
    monkeypatch.setattr(
        "app.core.tools.media_tools._save_image_asset",
        _fake_save,
    )


# --------------------------------------------------------------------- #
# generate_image 成功路径
# --------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_generate_image_default_model_is_pro(monkeypatch):
    """t2i 默认走 pro 模型，自动落 OSS + 落 Asset 表分配 asset_code。"""
    captured_gen: dict = {}
    captured_oss: dict = {}

    async def _fake_generate(**kwargs):
        captured_gen.update(kwargs)
        return _FakeImageResult(success=True, image_data=b"\x89PNG-fake", mime_type="image/png")

    def _fake_upload(data, filename, *, directory=None, unique=True):
        captured_oss["data"] = data
        captured_oss["filename"] = filename
        captured_oss["directory"] = directory
        return "https://oss/test/image.png"

    monkeypatch.setattr("app.utils.image_gen.image_gen_client.generate", _fake_generate)
    monkeypatch.setattr("app.utils.oss.oss_client.upload_bytes", _fake_upload)
    _patch_asset_save(monkeypatch, code="char-test-3view", asset_id=10)

    from app.core.tools.media_tools import generate_image

    result = await generate_image(
        prompt="一个少年站在悬崖边",
        aspect_ratio="9:16",
        image_size="2K",
        memory_harness=_FakeMemoryHarness(domain_id=1),
    )

    assert result["success"] is True
    assert result["asset_code"] == "char-test-3view"  # 来自 _patch_asset_save 的 mock
    assert result["asset_id"] == 10
    assert result["mode"] == "text2image"
    assert result["model"] == "gemini-3-pro-image-preview"
    assert result["aspect_ratio"] == "9:16"
    assert "url" not in result, "agent 不应看到 URL，只看 asset_code"
    assert captured_gen["prompt"] == "一个少年站在悬崖边"
    assert captured_gen["model"] == "gemini-3-pro-image-preview"
    assert captured_oss["directory"] == "supervisor/images"


@pytest.mark.asyncio
async def test_generate_image_explicit_flash_model(monkeypatch):
    seen_models: list[str] = []

    async def _fake_generate(**kwargs):
        seen_models.append(kwargs["model"])
        return _FakeImageResult(success=True, image_data=b"PNG")

    monkeypatch.setattr("app.utils.image_gen.image_gen_client.generate", _fake_generate)
    monkeypatch.setattr(
        "app.utils.oss.oss_client.upload_bytes",
        lambda *a, **kw: "https://oss/x.png",
    )
    _patch_asset_save(monkeypatch)

    from app.core.tools.media_tools import generate_image

    result = await generate_image(
        prompt="quick sketch",
        model="gemini-3.1-flash-image-preview",
        memory_harness=_FakeMemoryHarness(),
    )
    assert result["success"] is True
    assert result["model"] == "gemini-3.1-flash-image-preview"
    assert seen_models == ["gemini-3.1-flash-image-preview"]


# --------------------------------------------------------------------- #
# generate_image 失败路径
# --------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_generate_image_unknown_model_returns_tool_error(monkeypatch):
    """非法 model 应在调 utils 之前就拒绝。"""
    def _no_generate(**kwargs):
        raise AssertionError("非法 model 不应触达 utils")

    monkeypatch.setattr("app.utils.image_gen.image_gen_client.generate", _no_generate)

    from app.core.tools.media_tools import generate_image

    result = await generate_image(prompt="x", model="dall-e-3")
    assert result.get("ok") is False
    assert result["error_code"] == "IMAGE_MODEL_NOT_AVAILABLE"


@pytest.mark.asyncio
async def test_generate_image_tool_error_when_gen_fails(monkeypatch):
    async def _fake_generate(**kwargs):
        return _FakeImageResult(success=False, error_message="RAI blocked")

    monkeypatch.setattr("app.utils.image_gen.image_gen_client.generate", _fake_generate)

    def _no_upload(*a, **kw):
        raise AssertionError("失败时不应该再调 OSS")

    monkeypatch.setattr("app.utils.oss.oss_client.upload_bytes", _no_upload)

    from app.core.tools.media_tools import generate_image

    result = await generate_image(prompt="bad prompt", memory_harness=_FakeMemoryHarness())
    assert result.get("ok") is False
    assert result["error_code"] == "IMAGE_GEN_FAILED"
    assert "RAI blocked" in result["message"]


@pytest.mark.asyncio
async def test_generate_image_handles_gen_exception(monkeypatch):
    async def _raises(**kwargs):
        raise RuntimeError("network down")

    monkeypatch.setattr("app.utils.image_gen.image_gen_client.generate", _raises)

    from app.core.tools.media_tools import generate_image

    result = await generate_image(prompt="anything", memory_harness=_FakeMemoryHarness())
    assert result.get("ok") is False
    assert result["error_code"] == "IMAGE_GEN_EXCEPTION"
    assert "network down" in result["message"]


@pytest.mark.asyncio
async def test_generate_image_handles_oss_failure(monkeypatch):
    async def _fake_generate(**kwargs):
        return _FakeImageResult(success=True, image_data=b"PNG")

    def _bad_upload(*a, **kw):
        raise RuntimeError("oss 503")

    monkeypatch.setattr("app.utils.image_gen.image_gen_client.generate", _fake_generate)
    monkeypatch.setattr("app.utils.oss.oss_client.upload_bytes", _bad_upload)

    from app.core.tools.media_tools import generate_image

    result = await generate_image(prompt="x", memory_harness=_FakeMemoryHarness())
    assert result.get("ok") is False
    assert result["error_code"] == "OSS_UPLOAD_FAILED"


@pytest.mark.asyncio
async def test_generate_image_missing_project_id(monkeypatch):
    """没传 memory_harness → 无法解析 project_id，应早早返错。"""
    from app.core.tools.media_tools import generate_image

    result = await generate_image(prompt="x")
    assert result.get("ok") is False
    assert result["error_code"] == "PROJECT_ID_MISSING"


@pytest.mark.asyncio
async def test_generate_image_i2i_mode(monkeypatch):
    """asset_codes 非空 → 走 i2i，调 generate_with_reference。"""
    captured: dict = {}

    async def _fake_fetch(*, project_id, codes):
        captured["fetched_codes"] = codes
        captured["fetched_project_id"] = project_id
        return ([b"PNGREF"] * len(codes), [])

    async def _fake_with_ref(**kwargs):
        captured.update(kwargs)
        return _FakeImageResult(success=True, image_data=b"PNG")

    monkeypatch.setattr(
        "app.core.tools.media_tools._fetch_assets_bytes_by_code", _fake_fetch
    )
    monkeypatch.setattr(
        "app.utils.image_gen.image_gen_client.generate_with_reference", _fake_with_ref
    )
    monkeypatch.setattr(
        "app.utils.oss.oss_client.upload_bytes", lambda *a, **kw: "https://oss/y.png"
    )
    _patch_asset_save(monkeypatch, code="char-test-angry", asset_id=20)

    from app.core.tools.media_tools import generate_image

    result = await generate_image(
        prompt="angry close-up",
        asset_codes=["char-test-3view"],
        memory_harness=_FakeMemoryHarness(domain_id=7),
    )

    assert result["success"] is True
    assert result["mode"] == "image2image"
    assert result["asset_code"] == "char-test-angry"
    assert captured["fetched_codes"] == ["char-test-3view"]
    assert captured["fetched_project_id"] == 7
    assert captured["reference_images"] == [b"PNGREF"]


@pytest.mark.asyncio
async def test_generate_image_i2i_all_refs_missing(monkeypatch):
    """asset_codes 全部查不到 → REFERENCE_ASSETS_NOT_FOUND。"""
    async def _fake_fetch(*, project_id, codes):
        return ([], list(codes))

    monkeypatch.setattr(
        "app.core.tools.media_tools._fetch_assets_bytes_by_code", _fake_fetch
    )

    from app.core.tools.media_tools import generate_image

    result = await generate_image(
        prompt="x",
        asset_codes=["nonexistent-1", "nonexistent-2"],
        memory_harness=_FakeMemoryHarness(),
    )
    assert result.get("ok") is False
    assert result["error_code"] == "REFERENCE_ASSETS_NOT_FOUND"


# --------------------------------------------------------------------- #
# generate_video helpers
# --------------------------------------------------------------------- #


def _patch_video_asset_lookup(monkeypatch, urls: list[str], missing: list[str] | None = None):
    """绕过 assets 表查询：asset_code → file_url 解析。"""
    async def _fake_resolve(*, project_id, codes):
        return (urls, missing or [])
    monkeypatch.setattr(
        "app.core.tools.media_tools._resolve_asset_urls_by_code",
        _fake_resolve,
    )


def _patch_video_asset_save(monkeypatch, *, code: str = "vid-test", asset_id: int = 99):
    """绕过 Asset 表写入：直接 mock _save_video_asset 返 (code, id)。"""
    async def _fake_save(**kwargs):
        return (code, asset_id)
    monkeypatch.setattr(
        "app.core.tools.media_tools._save_video_asset",
        _fake_save,
    )


# --------------------------------------------------------------------- #
# generate_video 成功路径
# --------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_generate_video_success_with_asset_codes(monkeypatch):
    """成功路径：参考 asset_codes → Seedance 出片 → 自动入 assets 表分配 vid-xxx。"""
    captured_i2v: dict = {}
    captured_wait: dict = {}

    async def _fake_i2v(**kwargs):
        captured_i2v.update(kwargs)
        return _FakeVideoTask(id="seed-1", status="processing", video_url=None)

    async def _fake_wait(task_id, *args, **kwargs):
        captured_wait["task_id"] = task_id
        captured_wait["upload_to_oss"] = kwargs.get("upload_to_oss")
        captured_wait["oss_directory"] = kwargs.get("oss_directory")
        return _FakeVideoTask(
            id=task_id, status="completed",
            video_url="https://oss/v.mp4", video_duration=8.0,
        )

    monkeypatch.setattr("app.utils.seedance.seedance_client.image_to_video", _fake_i2v)
    monkeypatch.setattr(
        "app.utils.seedance.seedance_client.wait_for_completion", _fake_wait,
    )
    _patch_video_asset_lookup(monkeypatch, urls=["https://oss/ref-1.png", "https://oss/ref-2.png"])
    _patch_video_asset_save(monkeypatch, code="vid-abc1234567", asset_id=42)

    from app.core.tools.media_tools import generate_video

    result = await generate_video(
        prompt="角色冲入云海，参考图 1 服装、参考图 2 场景",
        asset_codes=["img-aaa", "img-bbb"],
        duration=8,
        aspect_ratio="9:16",
        generate_audio=False,
        description="第一幕 镜头 3",
        tags=["shot_3"],
        memory_harness=_FakeMemoryHarness(domain_id=1),
    )

    assert result["success"] is True
    assert result["asset_code"] == "vid-abc1234567"
    assert result["asset_id"] == 42
    assert result["url"] == "https://oss/v.mp4"
    assert result["task_id"] == "seed-1"
    assert result["model"] == "seedance-2.0-reference-to-video"
    assert result["duration"] == 8.0
    assert result["aspect_ratio"] == "9:16"
    assert result["generate_audio"] is False
    assert result["reference_codes"] == ["img-aaa", "img-bbb"]

    # 入参透传校验
    assert captured_i2v["prompt"].startswith("角色冲入云海")
    assert captured_i2v["image_urls"] == ["https://oss/ref-1.png", "https://oss/ref-2.png"]
    assert captured_i2v["duration"] == 8
    assert captured_i2v["aspect_ratio"] == "9:16"
    assert captured_i2v["generate_audio"] is False
    assert captured_wait["task_id"] == "seed-1"
    assert captured_wait["upload_to_oss"] is True
    assert captured_wait["oss_directory"] == "supervisor/videos"


# --------------------------------------------------------------------- #
# generate_video 校验路径
# --------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_generate_video_missing_project_id_returns_error():
    from app.core.tools.media_tools import generate_video

    result = await generate_video(prompt="x", asset_codes=["img-aaa"])  # 没 memory_harness
    assert result.get("ok") is False
    assert result["error_code"] == "PROJECT_ID_MISSING"


@pytest.mark.asyncio
async def test_generate_video_missing_asset_codes_returns_error(monkeypatch):
    """Seedance reference-to-video 不支持纯文生视频；空 asset_codes 应 fail-fast。"""
    async def _no_i2v(**kwargs):
        raise AssertionError("空 asset_codes 不应触达 seedance")

    monkeypatch.setattr("app.utils.seedance.seedance_client.image_to_video", _no_i2v)

    from app.core.tools.media_tools import generate_video

    result = await generate_video(
        prompt="x",
        asset_codes=None,
        memory_harness=_FakeMemoryHarness(),
    )
    assert result.get("ok") is False
    assert result["error_code"] == "ASSET_CODES_REQUIRED"


@pytest.mark.asyncio
async def test_generate_video_reference_assets_not_found(monkeypatch):
    """asset_codes 在 assets 表都查不到 → 不打 Seedance。"""
    async def _no_i2v(**kwargs):
        raise AssertionError("references 缺失时不应触达 seedance")

    monkeypatch.setattr("app.utils.seedance.seedance_client.image_to_video", _no_i2v)
    _patch_video_asset_lookup(monkeypatch, urls=[], missing=["img-nope"])

    from app.core.tools.media_tools import generate_video

    result = await generate_video(
        prompt="x",
        asset_codes=["img-nope"],
        memory_harness=_FakeMemoryHarness(),
    )
    assert result.get("ok") is False
    assert result["error_code"] == "REFERENCE_ASSETS_NOT_FOUND"


# --------------------------------------------------------------------- #
# generate_video 失败路径
# --------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_generate_video_returns_error_on_submit_exception(monkeypatch):
    async def _raise_i2v(**kwargs):
        raise RuntimeError("seedance 500")

    monkeypatch.setattr("app.utils.seedance.seedance_client.image_to_video", _raise_i2v)
    _patch_video_asset_lookup(monkeypatch, urls=["https://oss/ref.png"])

    from app.core.tools.media_tools import generate_video

    result = await generate_video(
        prompt="x",
        asset_codes=["img-aaa"],
        memory_harness=_FakeMemoryHarness(),
    )
    assert result.get("ok") is False
    assert result["error_code"] == "VIDEO_SUBMIT_FAILED"


@pytest.mark.asyncio
async def test_generate_video_returns_error_on_params_invalid(monkeypatch):
    """seedance 抛 ValueError（duration 越界等）→ VIDEO_PARAMS_INVALID。"""
    async def _bad_i2v(**kwargs):
        raise ValueError("duration 必须在 4-15 秒（当前 20）")

    monkeypatch.setattr("app.utils.seedance.seedance_client.image_to_video", _bad_i2v)
    _patch_video_asset_lookup(monkeypatch, urls=["https://oss/ref.png"])

    from app.core.tools.media_tools import generate_video

    result = await generate_video(
        prompt="x",
        asset_codes=["img-aaa"],
        duration=20,
        memory_harness=_FakeMemoryHarness(),
    )
    assert result.get("ok") is False
    assert result["error_code"] == "VIDEO_PARAMS_INVALID"


@pytest.mark.asyncio
async def test_generate_video_returns_error_when_seedance_fails(monkeypatch):
    async def _fake_i2v(**kwargs):
        return _FakeVideoTask(id="t-2")

    async def _fail_wait(task_id, *args, **kwargs):
        raise RuntimeError("seedance task failed")

    monkeypatch.setattr("app.utils.seedance.seedance_client.image_to_video", _fake_i2v)
    monkeypatch.setattr(
        "app.utils.seedance.seedance_client.wait_for_completion", _fail_wait,
    )
    _patch_video_asset_lookup(monkeypatch, urls=["https://oss/ref.png"])

    from app.core.tools.media_tools import generate_video

    result = await generate_video(
        prompt="x",
        asset_codes=["img-aaa"],
        memory_harness=_FakeMemoryHarness(),
    )
    assert result.get("ok") is False
    assert result["error_code"] == "VIDEO_GEN_FAILED"


@pytest.mark.asyncio
async def test_generate_video_propagates_seedance_internal_timeout(monkeypatch):
    """seedance.wait_for_completion 自己抛 TimeoutError → VIDEO_GEN_TIMEOUT。"""
    async def _fake_i2v(**kwargs):
        return _FakeVideoTask(id="t-3")

    async def _timeout_wait(task_id, *args, **kwargs):
        raise TimeoutError(f"Seedance 任务 {task_id} 超过 1200s 未完成")

    monkeypatch.setattr("app.utils.seedance.seedance_client.image_to_video", _fake_i2v)
    monkeypatch.setattr(
        "app.utils.seedance.seedance_client.wait_for_completion", _timeout_wait,
    )
    _patch_video_asset_lookup(monkeypatch, urls=["https://oss/ref.png"])

    from app.core.tools.media_tools import generate_video

    result = await generate_video(
        prompt="x",
        asset_codes=["img-aaa"],
        memory_harness=_FakeMemoryHarness(),
    )
    assert result.get("ok") is False
    assert result["error_code"] == "VIDEO_GEN_TIMEOUT"


@pytest.mark.asyncio
async def test_generate_video_outer_timeout_kills_hung_subtask(monkeypatch):
    """外层 asyncio.wait_for 兜底：哪怕 seedance 自己不超时，20 分钟硬上限也要把工具杀掉。

    用 monkeypatch 把 ``_VIDEO_TOOL_TIMEOUT_SECONDS`` 暂时改为极短值，再让内部 hang。
    """
    async def _hang_i2v(**kwargs):
        import asyncio as _aio
        await _aio.sleep(10)  # 永远跑不完
        return _FakeVideoTask(id="never")

    monkeypatch.setattr("app.utils.seedance.seedance_client.image_to_video", _hang_i2v)
    _patch_video_asset_lookup(monkeypatch, urls=["https://oss/ref.png"])
    monkeypatch.setattr(
        "app.core.tools.media_tools._VIDEO_TOOL_TIMEOUT_SECONDS",
        0.1,
    )

    from app.core.tools.media_tools import generate_video

    result = await generate_video(
        prompt="x",
        asset_codes=["img-aaa"],
        memory_harness=_FakeMemoryHarness(),
    )
    assert result.get("ok") is False
    assert result["error_code"] == "VIDEO_TOOL_TIMEOUT"
