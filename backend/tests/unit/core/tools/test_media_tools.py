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
# generate_video 成功路径
# --------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_generate_video_default_model_is_kling(monkeypatch):
    captured_t2v: dict = {}
    captured_wait: dict = {}

    async def _fake_t2v(**kwargs):
        captured_t2v.update(kwargs)
        return _FakeVideoTask(id="t-100", status="processing", video_url=None)

    async def _fake_wait(task_id, *args, **kwargs):
        captured_wait["task_id"] = task_id
        captured_wait["upload_to_oss"] = kwargs.get("upload_to_oss")
        captured_wait["oss_directory"] = kwargs.get("oss_directory")
        return _FakeVideoTask(
            id=task_id,
            status="completed",
            video_url="https://oss/v.mp4",
            video_duration=5.0,
        )

    monkeypatch.setattr("app.utils.evolink.evolink_client.text_to_video", _fake_t2v)
    monkeypatch.setattr(
        "app.utils.evolink.evolink_client.wait_for_completion",
        _fake_wait,
    )

    from app.core.tools.media_tools import generate_video

    result = await generate_video(
        prompt="一辆车驶过雨夜街道",
        duration=10,
        aspect_ratio="9:16",
        quality="hq",
    )

    assert result["success"] is True
    assert result["url"] == "https://oss/v.mp4"
    assert result["task_id"] == "t-100"
    assert result["model"] == "kling"
    assert result["quality"] == "1080p"  # hq → 1080p
    assert captured_t2v["prompt"] == "一辆车驶过雨夜街道"
    assert captured_t2v["duration"] == 10
    assert captured_t2v["aspect_ratio"] == "9:16"
    assert captured_t2v["quality"] == "1080p"
    assert captured_wait["task_id"] == "t-100"
    assert captured_wait["upload_to_oss"] is True
    assert captured_wait["oss_directory"] == "supervisor/videos"


@pytest.mark.asyncio
async def test_generate_video_std_maps_to_720p(monkeypatch):
    seen: dict = {}

    async def _fake_t2v(**kwargs):
        seen["quality"] = kwargs["quality"]
        return _FakeVideoTask(id="t-1")

    async def _fake_wait(task_id, *args, **kwargs):
        return _FakeVideoTask(id=task_id)

    monkeypatch.setattr("app.utils.evolink.evolink_client.text_to_video", _fake_t2v)
    monkeypatch.setattr(
        "app.utils.evolink.evolink_client.wait_for_completion", _fake_wait
    )

    from app.core.tools.media_tools import generate_video

    await generate_video(prompt="x")  # 默认 quality="std"
    assert seen["quality"] == "720p"


# --------------------------------------------------------------------- #
# generate_video model 路径
# --------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_generate_video_seedance_returns_model_not_available(monkeypatch):
    """seedance 占位模型不应触发 evolink，直接返回 MODEL_NOT_AVAILABLE。"""
    async def _no_t2v(**kwargs):
        raise AssertionError("seedance 路径不应调 evolink")

    async def _no_wait(*args, **kwargs):
        raise AssertionError("seedance 路径不应等待 evolink 任务")

    monkeypatch.setattr("app.utils.evolink.evolink_client.text_to_video", _no_t2v)
    monkeypatch.setattr(
        "app.utils.evolink.evolink_client.wait_for_completion", _no_wait
    )

    from app.core.tools.media_tools import generate_video

    result = await generate_video(prompt="anything", model="seedance")
    assert result.get("ok") is False
    assert result["error_code"] == "MODEL_NOT_AVAILABLE"


@pytest.mark.asyncio
async def test_generate_video_unknown_model_returns_video_model_not_available(monkeypatch):
    """完全未知的 model 应在 supported set 检查时拒绝。"""
    async def _no_t2v(**kwargs):
        raise AssertionError("未知 model 不应触达 evolink")

    monkeypatch.setattr("app.utils.evolink.evolink_client.text_to_video", _no_t2v)

    from app.core.tools.media_tools import generate_video

    result = await generate_video(prompt="x", model="sora")
    assert result.get("ok") is False
    assert result["error_code"] == "VIDEO_MODEL_NOT_AVAILABLE"


# --------------------------------------------------------------------- #
# generate_video 失败路径
# --------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_generate_video_returns_error_on_submit_exception(monkeypatch):
    async def _raise_t2v(**kwargs):
        raise RuntimeError("evolink 400")

    monkeypatch.setattr("app.utils.evolink.evolink_client.text_to_video", _raise_t2v)

    from app.core.tools.media_tools import generate_video

    result = await generate_video(prompt="bad")
    assert result.get("ok") is False
    assert result["error_code"] == "VIDEO_SUBMIT_FAILED"


@pytest.mark.asyncio
async def test_generate_video_returns_error_when_kling_fails(monkeypatch):
    async def _fake_t2v(**kwargs):
        return _FakeVideoTask(id="t-2")

    async def _fail_wait(task_id, *args, **kwargs):
        raise RuntimeError("kling task failed")

    monkeypatch.setattr("app.utils.evolink.evolink_client.text_to_video", _fake_t2v)
    monkeypatch.setattr(
        "app.utils.evolink.evolink_client.wait_for_completion", _fail_wait
    )

    from app.core.tools.media_tools import generate_video

    result = await generate_video(prompt="x")
    assert result.get("ok") is False
    assert result["error_code"] == "VIDEO_GEN_FAILED"
