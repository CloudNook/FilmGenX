"""
交互式 Agent CLI 辅助函数测试。
"""

import json
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BACKEND_ROOT))

from app.core.agent.base import AgentResult  # noqa: E402
from scripts.agent_cli import build_arg_parser, is_clear_command, is_exit_command, render_result_block  # noqa: E402


class TestAgentCliHelpers:
    def test_default_model_prefers_thinking_capable_variant(self):
        parser = build_arg_parser()
        args = parser.parse_args([])

        assert args.model == "gemini-3-pro-preview"

    def test_exit_command_detection(self):
        assert is_exit_command("exit") is True
        assert is_exit_command(" /quit ") is True
        assert is_exit_command("hello") is False

    def test_clear_command_detection(self):
        assert is_clear_command("/clear") is True
        assert is_clear_command(" clear ") is True
        assert is_clear_command("continue") is False

    def test_render_result_block_includes_schema_and_usage(self):
        result = AgentResult(
            agent_name="assistant",
            raw_output="最终回答",
            schema_data={"answer": "结构化答案", "used_tools": ["calculate"]},
            usage={"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
            loop_count=2,
            finished=True,
        )

        block = render_result_block(result)

        assert "最终回答" in block
        assert json.dumps(result.schema_data, ensure_ascii=False, indent=2) in block
        assert "total_tokens" in block
        assert "loop_count" in block
