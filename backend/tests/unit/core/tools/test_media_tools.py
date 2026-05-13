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
# generate_image（Evolink GPT-Image-2）
#
# 历史：之前有一份 Gemini 原生 generate_image，已经删除——现在 generate_image 就是
# 走 Evolink 的实现。本组覆盖 t2i 成功 / i2i 成功 / 校验失败 / 引用缺失。
# --------------------------------------------------------------------- #


class _FakeEvolinkImageTask:
    """模拟 evolink_client.image_generation / wait_for_completion 的 EvolinkTask 返值。"""

    def __init__(
        self,
        *,
        id: str = "task-1",
        status: str = "completed",
        results: list[str] | None = None,
    ):
        self.id = id
        self.status = status
        self.results = results if results is not None else ["https://oss/img.png"]


def _patch_evolink_image_pipeline(
    monkeypatch,
    *,
    submit_capture: dict | None = None,
    result_urls: list[str] | None = None,
):
    """同时 patch image_generation + wait_for_completion + _save_image_asset + asset_url_lookup。"""
    captured = submit_capture if submit_capture is not None else {}

    async def _fake_submit(**kwargs):
        captured.update(kwargs)
        return _FakeEvolinkImageTask(id="task-x", status="processing", results=[])

    async def _fake_wait(task_id, *args, **kwargs):
        return _FakeEvolinkImageTask(
            id=task_id, status="completed",
            results=result_urls or ["https://oss/img.png"],
        )

    monkeypatch.setattr("app.utils.evolink.evolink_client.image_generation", _fake_submit)
    monkeypatch.setattr("app.utils.evolink.evolink_client.wait_for_completion", _fake_wait)
    return captured


@pytest.mark.asyncio
async def test_generate_image_t2i_success(monkeypatch):
    """asset_codes 不传 → t2i：直接 submit Evolink，落 assets 表。"""
    captured = _patch_evolink_image_pipeline(monkeypatch, result_urls=["https://oss/a.png"])
    _patch_asset_save(monkeypatch, code="img-aaa", asset_id=42)

    from app.core.tools.media_tools import generate_image

    result = await generate_image(
        prompt="一个少年站在悬崖边",
        name="萧炎",
        aspect_ratio="9:16",
        resolution="2K",
        quality="high",
        memory_harness=_FakeMemoryHarness(domain_id=1),
    )

    assert result["success"] is True
    assert result["mode"] == "text2image"
    assert result["model"] == "gpt-image-2"
    assert result["asset_code"] == "img-aaa"
    assert result["asset_id"] == 42
    assert result["url"] == "https://oss/a.png"

    # 入参透传到 Evolink
    assert captured["prompt"] == "一个少年站在悬崖边"
    assert captured["size"] == "9:16"
    assert captured["resolution"] == "2K"
    assert captured["quality"] == "high"
    assert captured["n"] == 1
    assert captured.get("image_urls") is None, "t2i 不该传 image_urls"


@pytest.mark.asyncio
async def test_generate_image_i2i_passes_image_urls(monkeypatch):
    """asset_codes 非空 → 解析为 URL → 喂给 Evolink image_urls 字段。"""
    captured = _patch_evolink_image_pipeline(monkeypatch, result_urls=["https://oss/i2i.png"])
    _patch_asset_save(monkeypatch, code="img-bbb", asset_id=99)

    # mock asset_code → URL 解析
    async def _fake_resolve(*, project_id, codes):
        return (["https://oss/ref1.png", "https://oss/ref2.png"], [])
    monkeypatch.setattr(
        "app.core.tools.media_tools._resolve_asset_urls_by_code", _fake_resolve,
    )

    from app.core.tools.media_tools import generate_image

    result = await generate_image(
        prompt="把场景改成雨夜",
        name="云岚宗-雨夜",
        asset_codes=["img-base-1", "img-base-2"],
        memory_harness=_FakeMemoryHarness(),
    )

    assert result["success"] is True
    assert result["mode"] == "image2image"
    assert result["asset_code"] == "img-bbb"
    # image_urls 是 GPT-Image-2 接受的字段名，按 asset_codes 顺序解析
    assert captured["image_urls"] == ["https://oss/ref1.png", "https://oss/ref2.png"]


@pytest.mark.asyncio
async def test_generate_image_missing_project_id():
    """没传 memory_harness → 无法解析 project_id，应早早返错。"""
    from app.core.tools.media_tools import generate_image

    result = await generate_image(prompt="x", name="test-asset")
    assert result.get("ok") is False
    assert result["error_code"] == "PROJECT_ID_MISSING"


@pytest.mark.asyncio
async def test_generate_image_i2i_all_refs_missing(monkeypatch):
    """asset_codes 全部查不到 → REFERENCE_ASSETS_NOT_FOUND，不打 Evolink。"""
    async def _fake_resolve(*, project_id, codes):
        return ([], list(codes))
    monkeypatch.setattr(
        "app.core.tools.media_tools._resolve_asset_urls_by_code", _fake_resolve,
    )

    async def _no_submit(**kwargs):
        raise AssertionError("references 全缺失时不应触达 Evolink")
    monkeypatch.setattr("app.utils.evolink.evolink_client.image_generation", _no_submit)

    from app.core.tools.media_tools import generate_image

    result = await generate_image(
        prompt="x",
        name="test-asset",
        asset_codes=["nonexistent-1", "nonexistent-2"],
        memory_harness=_FakeMemoryHarness(),
    )
    assert result.get("ok") is False
    assert result["error_code"] == "REFERENCE_ASSETS_NOT_FOUND"


@pytest.mark.asyncio
async def test_generate_image_n_out_of_range():
    """n=6 超过单次上限 5 → 早 fail-fast。"""
    from app.core.tools.media_tools import generate_image

    result = await generate_image(
        prompt="x", name="test-asset", n=6, memory_harness=_FakeMemoryHarness(),
    )
    assert result.get("ok") is False
    assert result["error_code"] == "N_OUT_OF_RANGE"


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
        name="test-asset",
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
    # @图片N 映射按 asset_codes 顺序 1-indexed
    assert result["image_refs"] == {
        "@图片1": "img-aaa",
        "@图片2": "img-bbb",
    }
    # _FakeMemoryHarness 没装 provider → 反查不到 KV 名 → name_refs 为空
    assert result["name_refs"] == {}

    # 入参透传校验
    assert captured_i2v["prompt"].startswith("角色冲入云海")
    assert captured_i2v["image_urls"] == ["https://oss/ref-1.png", "https://oss/ref-2.png"]
    assert captured_i2v["duration"] == 8
    assert captured_i2v["aspect_ratio"] == "9:16"
    assert captured_i2v["generate_audio"] is False
    assert captured_wait["task_id"] == "seed-1"
    assert captured_wait["upload_to_oss"] is True
    assert captured_wait["oss_directory"] == "supervisor/videos"


def _patch_asset_names_lookup(monkeypatch, *, code_to_name: dict):
    """绕过 assets.name DB 查询：直接 mock _lookup_asset_names_by_code 返预设映射。"""
    async def _fake_lookup(*, project_id, codes):
        return {code: code_to_name[code] for code in codes if code in code_to_name}
    monkeypatch.setattr(
        "app.core.tools.media_tools._lookup_asset_names_by_code",
        _fake_lookup,
    )


@pytest.mark.asyncio
async def test_generate_video_prepends_name_aliases_from_asset_name(monkeypatch):
    """assets.name 里能反查到名字时，prompt 头部自动注入 ``名=@图片N`` 别名行。"""
    captured_i2v: dict = {}

    async def _fake_i2v(**kwargs):
        captured_i2v.update(kwargs)
        return _FakeVideoTask(id="seed-named", status="processing", video_url=None)

    async def _fake_wait(task_id, *args, **kwargs):
        return _FakeVideoTask(
            id=task_id, status="completed",
            video_url="https://oss/v.mp4", video_duration=5.0,
        )

    monkeypatch.setattr("app.utils.seedance.seedance_client.image_to_video", _fake_i2v)
    monkeypatch.setattr(
        "app.utils.seedance.seedance_client.wait_for_completion", _fake_wait,
    )
    _patch_video_asset_lookup(monkeypatch, urls=["https://oss/r1.png", "https://oss/r2.png"])
    _patch_video_asset_save(monkeypatch, code="vid-named", asset_id=77)
    # img-xy.name = "萧炎"; img-yl.name = "云岚宗广场"
    _patch_asset_names_lookup(monkeypatch, code_to_name={"img-xy": "萧炎", "img-yl": "云岚宗广场"})

    from app.core.tools.media_tools import generate_video

    result = await generate_video(
        prompt="角色冲入云海，镜头缓推",
        name="test-asset",
        asset_codes=["img-xy", "img-yl"],
        memory_harness=_FakeMemoryHarness(),
    )

    assert result["success"] is True
    assert result["name_refs"] == {"萧炎": "@图片1", "云岚宗广场": "@图片2"}
    # prompt 头部已被前置别名行
    assert captured_i2v["prompt"].startswith("素材引用：萧炎=@图片1，云岚宗广场=@图片2\n\n")
    assert "角色冲入云海" in captured_i2v["prompt"]


@pytest.mark.asyncio
async def test_generate_video_no_alias_when_assets_have_no_name(monkeypatch):
    """asset 没填 name → name_refs 为空，prompt 不前置别名行。"""
    captured_i2v: dict = {}

    async def _fake_i2v(**kwargs):
        captured_i2v.update(kwargs)
        return _FakeVideoTask(id="x", status="processing", video_url=None)

    async def _fake_wait(task_id, *args, **kwargs):
        return _FakeVideoTask(
            id=task_id, status="completed",
            video_url="https://oss/v.mp4", video_duration=5.0,
        )

    monkeypatch.setattr("app.utils.seedance.seedance_client.image_to_video", _fake_i2v)
    monkeypatch.setattr(
        "app.utils.seedance.seedance_client.wait_for_completion", _fake_wait,
    )
    _patch_video_asset_lookup(monkeypatch, urls=["https://oss/r.png"])
    _patch_video_asset_save(monkeypatch, code="vid-z", asset_id=1)
    _patch_asset_names_lookup(monkeypatch, code_to_name={})  # 啥 name 都没有

    from app.core.tools.media_tools import generate_video

    result = await generate_video(
        prompt="缓推镜头",
        name="test-asset",
        asset_codes=["img-anon"],
        memory_harness=_FakeMemoryHarness(),
    )
    assert result["success"] is True
    assert result["name_refs"] == {}
    # prompt 原文，没前置素材引用行
    assert captured_i2v["prompt"] == "缓推镜头"


@pytest.mark.asyncio
async def test_generate_video_rejects_out_of_range_image_ref(monkeypatch):
    """prompt 引用 @图片3 但只传了 2 张参考图 → fail-fast，不打 Seedance。"""
    async def _no_i2v(**kwargs):
        raise AssertionError("越界引用不应触达 seedance")

    monkeypatch.setattr("app.utils.seedance.seedance_client.image_to_video", _no_i2v)
    _patch_video_asset_lookup(monkeypatch, urls=["https://oss/r1.png", "https://oss/r2.png"])

    from app.core.tools.media_tools import generate_video

    result = await generate_video(
        prompt="@图片1 与 @图片3 互动",
        name="test-asset",
        asset_codes=["img-a", "img-b"],
        memory_harness=_FakeMemoryHarness(),
    )
    assert result.get("ok") is False
    assert result["error_code"] == "VIDEO_PROMPT_REF_OUT_OF_RANGE"
    assert result["context"]["out_of_range"] == [3]
    assert result["context"]["ref_count"] == 2


# --------------------------------------------------------------------- #
# generate_video 校验路径
# --------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_generate_video_missing_project_id_returns_error():
    from app.core.tools.media_tools import generate_video

    result = await generate_video(name="test-asset", prompt="x", asset_codes=["img-aaa"])  # 没 memory_harness
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
        name="test-asset",
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
        name="test-asset",
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
        name="test-asset",
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
        name="test-asset",
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
        name="test-asset",
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
        name="test-asset",
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
        name="test-asset",
        asset_codes=["img-aaa"],
        memory_harness=_FakeMemoryHarness(),
    )
    assert result.get("ok") is False
    assert result["error_code"] == "VIDEO_TOOL_TIMEOUT"


# --------------------------------------------------------------------- #
# concat_videos —— 按顺序拼接多段视频成成片
# --------------------------------------------------------------------- #


class _FakeVideoAsset:
    """模拟 Asset ORM 行：concat_videos 只读 asset_code / asset_type / file_url /
    duration_sec / tags。"""

    def __init__(
        self,
        *,
        asset_code: str,
        file_url: str,
        duration_sec: float,
        aspect_ratio: str = "16:9",
        asset_type: str = "video",
        tags: list[str] | None = None,
    ):
        self.asset_code = asset_code
        self.file_url = file_url
        self.duration_sec = duration_sec
        self.asset_type = asset_type
        # 仿照 generate_video 实际入库的 tag 结构
        self.tags = (tags or []) + [f"aspect_ratio:{aspect_ratio}"]


def _patch_concat_lookup(
    monkeypatch,
    assets_by_code: dict[str, _FakeVideoAsset],
    *,
    missing: list[str] | None = None,
):
    """patch ``_lookup_video_assets_by_code`` 直接返预设映射，保持输入顺序。"""

    async def _fake_lookup(*, project_id, codes):
        ordered: list[_FakeVideoAsset] = []
        not_found: list[str] = list(missing or [])
        for code in codes:
            if code in (missing or []):
                continue
            asset = assets_by_code.get(code)
            if asset is None:
                not_found.append(code)
                continue
            ordered.append(asset)
        return ordered, not_found

    monkeypatch.setattr(
        "app.core.tools.media_tools._lookup_video_assets_by_code",
        _fake_lookup,
    )


def _patch_concat_pipeline_success(
    monkeypatch,
    *,
    merged_bytes: bytes = b"\x00\x00\x00\x18ftypmp42fakebytes",
    total_duration: float = 30.0,
):
    """patch ffmpeg 管道：跳过实际下载 / 拼接，直接返预设 bytes + duration。"""

    async def _fake_pipeline(sources):
        return merged_bytes, total_duration

    monkeypatch.setattr(
        "app.core.tools.media_tools._concat_video_pipeline",
        _fake_pipeline,
    )


def _patch_oss_upload_concat(monkeypatch, *, url: str = "https://oss/concat/final.mp4"):
    """绕过 OSS 实际上传，返预设 URL。"""

    class _FakeOSS:
        def upload_bytes(self, data, *, filename, directory=None, unique=True):
            return url

    monkeypatch.setattr("app.utils.oss.oss_client", _FakeOSS())


def _patch_video_asset_save(monkeypatch, *, code: str = "vid-final", asset_id: int = 999):
    """绕过 _save_video_asset DB 写入。"""

    async def _fake_save(**kwargs):
        return (code, asset_id)

    monkeypatch.setattr(
        "app.core.tools.media_tools._save_video_asset",
        _fake_save,
    )


@pytest.mark.asyncio
async def test_concat_videos_success_orders_by_input(monkeypatch):
    """成功路径：3 段同 aspect_ratio 视频 → 拼成一段，duration 累加，segment_count=3。"""
    assets = {
        "vid-shot1": _FakeVideoAsset(
            asset_code="vid-shot1", file_url="https://oss/s1.mp4", duration_sec=5
        ),
        "vid-shot2": _FakeVideoAsset(
            asset_code="vid-shot2", file_url="https://oss/s2.mp4", duration_sec=8
        ),
        "vid-shot3": _FakeVideoAsset(
            asset_code="vid-shot3", file_url="https://oss/s3.mp4", duration_sec=7
        ),
    }
    _patch_concat_lookup(monkeypatch, assets)
    _patch_concat_pipeline_success(monkeypatch, total_duration=20.0)
    _patch_oss_upload_concat(monkeypatch, url="https://oss/concat/final.mp4")
    _patch_video_asset_save(monkeypatch, code="vid-finalcut", asset_id=99)

    from app.core.tools.media_tools import concat_videos

    result = await concat_videos(
        asset_codes=["vid-shot1", "vid-shot2", "vid-shot3"],
        name="云岚宗短剧·完整 20s",
        description="3 段拼接测试",
        tags=["final-cut"],
        memory_harness=_FakeMemoryHarness(domain_id=1),
    )

    assert result["success"] is True
    assert result["asset_code"] == "vid-finalcut"
    assert result["asset_id"] == 99
    assert result["url"] == "https://oss/concat/final.mp4"
    assert result["segment_count"] == 3
    assert result["total_duration_seconds"] == 20.0
    assert result["aspect_ratio"] == "16:9"
    # source_codes 保持输入顺序
    assert result["source_codes"] == ["vid-shot1", "vid-shot2", "vid-shot3"]


@pytest.mark.asyncio
async def test_concat_videos_missing_project_id_returns_error():
    from app.core.tools.media_tools import concat_videos

    result = await concat_videos(
        asset_codes=["vid-a", "vid-b"],
        name="test",
        memory_harness=None,
    )
    assert result.get("ok") is False
    assert result["error_code"] == "PROJECT_ID_MISSING"


@pytest.mark.asyncio
async def test_concat_videos_rejects_single_segment(monkeypatch):
    """只传 1 个 code → 拒：拼接没意义。"""
    from app.core.tools.media_tools import concat_videos

    result = await concat_videos(
        asset_codes=["vid-only"],
        name="test",
        memory_harness=_FakeMemoryHarness(),
    )
    assert result.get("ok") is False
    assert result["error_code"] == "ASSET_CODES_TOO_FEW"


@pytest.mark.asyncio
async def test_concat_videos_rejects_bad_type(monkeypatch):
    """asset_codes 是 dict / int 等非 list[str] → 结构化错误。
    （单 string "vid-a" 会被 normalize 当 1-element list 宽容处理，不算 BAD_TYPE。）"""
    from app.core.tools.media_tools import concat_videos

    result = await concat_videos(
        asset_codes={"shot1": "vid-a"},  # type: ignore[arg-type]
        name="test",
        memory_harness=_FakeMemoryHarness(),
    )
    assert result.get("ok") is False
    assert result["error_code"] == "ASSET_CODES_BAD_TYPE"


@pytest.mark.asyncio
async def test_concat_videos_missing_code_returns_error(monkeypatch):
    """asset_code 在 DB 查不到 → 结构化错误，列出 missing。"""
    assets = {
        "vid-shot1": _FakeVideoAsset(
            asset_code="vid-shot1", file_url="https://oss/s1.mp4", duration_sec=5
        ),
    }
    _patch_concat_lookup(monkeypatch, assets, missing=["vid-ghost"])

    from app.core.tools.media_tools import concat_videos

    result = await concat_videos(
        asset_codes=["vid-shot1", "vid-ghost"],
        name="test",
        memory_harness=_FakeMemoryHarness(),
    )
    assert result.get("ok") is False
    assert result["error_code"] == "ASSET_CODES_NOT_FOUND"
    assert "vid-ghost" in result["context"]["missing"]


@pytest.mark.asyncio
async def test_concat_videos_rejects_non_video_asset(monkeypatch):
    """asset_type != 'video' → 拒（避免误把图片传进来）。"""
    assets = {
        "vid-shot1": _FakeVideoAsset(
            asset_code="vid-shot1", file_url="https://oss/s1.mp4", duration_sec=5
        ),
        "img-shot2": _FakeVideoAsset(
            asset_code="img-shot2",
            file_url="https://oss/s2.png",
            duration_sec=0,
            asset_type="image",
        ),
    }
    _patch_concat_lookup(monkeypatch, assets)

    from app.core.tools.media_tools import concat_videos

    result = await concat_videos(
        asset_codes=["vid-shot1", "img-shot2"],
        name="test",
        memory_harness=_FakeMemoryHarness(),
    )
    assert result.get("ok") is False
    assert result["error_code"] == "ASSET_NOT_VIDEO"
    assert "img-shot2" in result["context"]["non_video"]


@pytest.mark.asyncio
async def test_concat_videos_rejects_aspect_ratio_mismatch(monkeypatch):
    """aspect_ratio 不一致 → 拒，列出每段的 aspect_ratio 供 agent 决定哪段重出。"""
    assets = {
        "vid-shot1": _FakeVideoAsset(
            asset_code="vid-shot1", file_url="https://oss/s1.mp4",
            duration_sec=5, aspect_ratio="16:9",
        ),
        "vid-shot2": _FakeVideoAsset(
            asset_code="vid-shot2", file_url="https://oss/s2.mp4",
            duration_sec=5, aspect_ratio="9:16",
        ),
    }
    _patch_concat_lookup(monkeypatch, assets)

    from app.core.tools.media_tools import concat_videos

    result = await concat_videos(
        asset_codes=["vid-shot1", "vid-shot2"],
        name="test",
        memory_harness=_FakeMemoryHarness(),
    )
    assert result.get("ok") is False
    assert result["error_code"] == "ASPECT_RATIO_MISMATCH"
    assert set(result["context"]["aspect_ratios"]) == {"16:9", "9:16"}


@pytest.mark.asyncio
async def test_concat_videos_ffmpeg_pipeline_failure_reported(monkeypatch):
    """_concat_video_pipeline 抛 _ConcatError → 结构化错误向上透传。"""
    assets = {
        "vid-shot1": _FakeVideoAsset(
            asset_code="vid-shot1", file_url="https://oss/s1.mp4", duration_sec=5
        ),
        "vid-shot2": _FakeVideoAsset(
            asset_code="vid-shot2", file_url="https://oss/s2.mp4", duration_sec=5
        ),
    }
    _patch_concat_lookup(monkeypatch, assets)

    from app.core.tools.media_tools import _ConcatError

    async def _explode(sources):
        raise _ConcatError(
            code="FFMPEG_FAILED",
            message="ffmpeg 拼接失败",
            hint="检查二进制",
        )

    monkeypatch.setattr("app.core.tools.media_tools._concat_video_pipeline", _explode)

    from app.core.tools.media_tools import concat_videos

    result = await concat_videos(
        asset_codes=["vid-shot1", "vid-shot2"],
        name="test",
        memory_harness=_FakeMemoryHarness(),
    )
    assert result.get("ok") is False
    assert result["error_code"] == "FFMPEG_FAILED"


@pytest.mark.asyncio
async def test_concat_videos_preserves_input_order(monkeypatch):
    """输入顺序 = 输出顺序：source_codes 字段必须反映 agent 传入的播放序。"""
    assets = {
        "vid-a": _FakeVideoAsset(asset_code="vid-a", file_url="https://oss/a.mp4", duration_sec=5),
        "vid-b": _FakeVideoAsset(asset_code="vid-b", file_url="https://oss/b.mp4", duration_sec=5),
        "vid-c": _FakeVideoAsset(asset_code="vid-c", file_url="https://oss/c.mp4", duration_sec=5),
    }
    _patch_concat_lookup(monkeypatch, assets)
    _patch_concat_pipeline_success(monkeypatch)
    _patch_oss_upload_concat(monkeypatch)
    _patch_video_asset_save(monkeypatch)

    from app.core.tools.media_tools import concat_videos

    # 反向输入——验证不被字典序 / 任何 reordering 干扰
    result = await concat_videos(
        asset_codes=["vid-c", "vid-a", "vid-b"],
        name="reverse-order-test",
        memory_harness=_FakeMemoryHarness(),
    )
    assert result["success"] is True
    assert result["source_codes"] == ["vid-c", "vid-a", "vid-b"]
