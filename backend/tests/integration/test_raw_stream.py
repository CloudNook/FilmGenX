#!/usr/bin/env python
# coding: utf-8
"""
直接用 Google SDK 打印 Gemini 流式响应的原始 chunk JSON。
"""

import asyncio
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BACKEND_ROOT))

from dotenv import load_dotenv
load_dotenv(BACKEND_ROOT / ".env")

import os

key = os.environ.get("GOOGLE_API_KEY", "")
print(f"API key: {'yes' if key else 'NO'}\n")

from google import genai
from google.genai import types


async def main():
    client = genai.Client(api_key=key)

    contents = [{"role": "user", "parts": [{"text": "为什么天空是蓝色的？"}]}]
    config = types.GenerateContentConfig(
        system_instruction={
            "parts": [{
                "text": "你是一个严谨的助手。在给出最终回答之前，必须先用思考过程(thinking)详细分析问题、列出推理步骤，最后再给出结论。"
            }]
        },
        thinking_config=types.ThinkingConfig(thinking_budget=-1, include_thoughts=True),
    )

    print("=== Google SDK 原始流式响应 (include_thoughts=True) ===\n")

    stream = await client.aio.models.generate_content_stream(
        model="gemini-3-pro-preview",
        contents=contents,
        config=config,
    )

    chunk_num = 0
    async for raw_chunk in stream:
        chunk_num += 1
        if chunk_num > 5:
            break
        print(f"[{chunk_num:3d}] {raw_chunk.model_dump_json(indent=2, ensure_ascii=False)}")

    print(f"\n--- 共 {chunk_num} 个原始 chunk ---")


if __name__ == "__main__":
    asyncio.run(main())
