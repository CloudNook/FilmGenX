"""
Redis 客户端封装。

提供同步/异步 Redis 操作接口，基于 redis-py。
"""

import json
import logging
from typing import Any, Optional

import redis.asyncio as redis

from app.core.config import settings

logger = logging.getLogger(__name__)

# 全局异步客户端
_async_client: Optional[redis.Redis] = None


def get_async_client() -> redis.Redis:
    """
    获取全局异步 Redis 客户端（单例）。

    Returns:
        redis.Redis 实例
    """
    global _async_client
    if _async_client is None:
        _async_client = redis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
        )
        logger.info(f"[Redis] Connected to {settings.REDIS_URL}")
    return _async_client


async def close_async_client() -> None:
    """关闭全局异步客户端。"""
    global _async_client
    if _async_client is not None:
        await _async_client.close()
        _async_client = None
        logger.info("[Redis] Connection closed")


# ── 通用 Key-Value 操作 ──────────────────────────────────────────


async def get(key: str) -> Optional[str]:
    """根据 key 获取值。"""
    client = get_async_client()
    return await client.get(key)


async def set(
    key: str,
    value: str,
    *,
    ex: Optional[int] = None,
    px: Optional[int] = None,
    ttl: Optional[int] = None,
) -> bool:
    """
    设置 key-value。

    Args:
        key: 键
        value: 值（字符串）
        ex: 过期时间（秒）
        px: 过期时间（毫秒）
        ttl: 过期时间（秒），优先级高于 ex

    Returns:
        成功返回 True
    """
    client = get_async_client()
    expire = ttl if ttl is not None else ex
    return bool(await client.set(key, value, ex=expire, px=px))


async def delete(*keys: str) -> int:
    """删除一个或多个 key。"""
    if not keys:
        return 0
    client = get_async_client()
    return await client.delete(*keys)


async def exists(key: str) -> bool:
    """检查 key 是否存在。"""
    client = get_async_client()
    return bool(await client.exists(key))


async def expire(key: str, seconds: int) -> bool:
    """设置 key 的过期时间。"""
    client = get_async_client()
    return bool(await client.expire(key, seconds))


# ── JSON 操作 ──────────────────────────────────────────────────


async def get_json(key: str) -> Optional[Any]:
    """读取 JSON 值（自动反序列化）。"""
    raw = await get(key)
    if raw is None:
        return None
    return json.loads(raw)


async def set_json(
    key: str,
    value: Any,
    *,
    ex: Optional[int] = None,
    ttl: Optional[int] = None,
) -> bool:
    """
    写入 JSON 值（自动序列化）。

    Args:
        key: 键
        value: 任意可序列化对象
        ex: 过期时间（秒）
        ttl: 同 ex

    Returns:
        成功返回 True
    """
    serialized = json.dumps(value, ensure_ascii=False)
    return await set(key, serialized, ex=ex, ttl=ttl)


# ── List 操作 ──────────────────────────────────────────────────


async def lpush(key: str, *values: str) -> int:
    """从左侧 push（栈操作）。"""
    client = get_async_client()
    return await client.lpush(key, *values)


async def rpush(key: str, *values: str) -> int:
    """从右侧 push（队列操作）。"""
    client = get_async_client()
    return await client.rpush(key, *values)


async def lrange(key: str, start: int = 0, end: int = -1) -> list[str]:
    """读取列表片段。"""
    client = get_async_client()
    return await client.lrange(key, start, end)


async def llen(key: str) -> int:
    """获取列表长度。"""
    client = get_async_client()
    return await client.llen(key)


async def ltrim(key: str, start: int, end: int) -> bool:
    """裁剪列表，保留指定区间。"""
    client = get_async_client()
    return bool(await client.ltrim(key, start, end))


# ── Hash 操作 ──────────────────────────────────────────────────


async def hset(key: str, field: str, value: str) -> int:
    """设置 Hash 字段。"""
    client = get_async_client()
    return await client.hset(key, field, value)


async def hget(key: str, field: str) -> Optional[str]:
    """读取 Hash 字段。"""
    client = get_async_client()
    return await client.hget(key, field)


async def hgetall(key: str) -> dict[str, str]:
    """读取 Hash 所有字段。"""
    client = get_async_client()
    return await client.hgetall(key)


async def hdel(key: str, *fields: str) -> int:
    """删除 Hash 字段。"""
    client = get_async_client()
    return await client.hdel(key, *fields)
