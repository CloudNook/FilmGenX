"""
Token usage 工具函数。
"""

from typing import Any, Dict, Optional


def merge_usage(
    base: Optional[Dict[str, Any]],
    delta: Optional[Dict[str, Any]],
) -> Optional[Dict[str, Any]]:
    """
    合并两份 usage 数据。

    数值字段累加，非数值字段以后者为准。
    """
    if not base and not delta:
        return None

    merged: Dict[str, Any] = dict(base or {})
    for key, value in (delta or {}).items():
        if value is None:
            # None 不覆盖已有数值，跳过
            if key not in merged:
                merged[key] = value
        elif isinstance(value, (int, float)) and isinstance(merged.get(key), (int, float)):
            merged[key] += value
        else:
            merged[key] = value
    return merged
