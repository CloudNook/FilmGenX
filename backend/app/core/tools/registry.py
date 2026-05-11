"""
Tool 注册表 - 装饰器式工具注册。

支持：
1. 装饰器注册：@register_tool(name="xxx")
2. 自动发现：ToolRegistry.discover(package="app.tools")
"""

import inspect
import logging
import typing
from types import UnionType
from typing import Any, Callable, Dict, Optional, Union, get_args, get_origin

logger = logging.getLogger(__name__)


class ToolFunc:
    """
    工具函数封装。

    包装一个普通函数，附带元数据，供 Agent 调用。
    """

    def __init__(
        self,
        func: Callable[..., Any],
        name: str,
        description: str = "",
        parameters_schema: Optional[Dict[str, Any]] = None,
    ):
        self.func = func
        self.name = name
        self.description = description or func.__doc__ or ""
        self.parameters_schema = parameters_schema or self._infer_schema(func)

    # 框架运行时注入的参数，不属于工具接口，不暴露给 LLM
    _INJECTED_PARAMS = frozenset({
        "db",
        "supervisor_context",
        "workflow_store",
        "memory_harness",   # MemoryHarness 实例，agent.py 通过 ToolExecutor.extra_kwargs 注入
    })

    def _annotation_to_schema(self, annotation: Any) -> Dict[str, Any]:
        if annotation == inspect.Parameter.empty:
            return {"type": "string"}
        if annotation in (int, "int"):
            return {"type": "integer"}
        if annotation in (float, "float"):
            return {"type": "number"}
        if annotation in (bool, "bool"):
            return {"type": "boolean"}
        if annotation in (list, "list", tuple, "tuple", set, "set"):
            return {"type": "array", "items": {"type": "string"}}
        if annotation in (dict, "dict"):
            return {"type": "object"}

        origin = get_origin(annotation)
        args = get_args(annotation)

        if origin in (list, tuple, set):
            item_annotation = args[0] if args else inspect.Parameter.empty
            return {
                "type": "array",
                "items": self._annotation_to_schema(item_annotation),
            }

        if origin is dict:
            return {"type": "object"}

        if origin in (UnionType, Union):
            non_none_args = [arg for arg in args if arg is not type(None)]
            if len(non_none_args) == 1:
                return self._annotation_to_schema(non_none_args[0])

        return {"type": "string"}

    def _infer_schema(self, func: Callable) -> Dict[str, Any]:
        """从函数签名推断 JSON Schema。

        关键：用 ``typing.get_type_hints`` 而不是 ``inspect.signature.annotation``——
        启用了 ``from __future__ import annotations`` 的模块里，annotation 是字符串
        ``"Optional[list[str]]"``，``inspect`` 拿到的是原文，我们的类型 dispatch 全部
        fallthrough 到 ``{"type": "string"}``。``get_type_hints`` 会把字符串解析回真实
        泛型对象，list / dict / Union 才能被识别。
        """
        sig = inspect.signature(func)
        try:
            resolved_hints = typing.get_type_hints(func)
        except Exception:
            # 解析失败（typing 引用了运行时不可见的符号等）退回原始 annotation
            resolved_hints = {}

        properties = {}
        required = []
        for param_name, param in sig.parameters.items():
            # self/cls：Python 语言层面，不是参数
            if param_name in ("self", "cls"):
                continue
            # db 等：ToolExecutor 运行时注入，不是工具接口的一部分
            if param_name in self._INJECTED_PARAMS:
                continue

            annotation = resolved_hints.get(param_name, param.annotation)
            properties[param_name] = self._annotation_to_schema(annotation)
            if param.default == inspect.Parameter.empty:
                required.append(param_name)

        return {
            "type": "object",
            "properties": properties,
            "required": required,
        }

    def get_schema(self) -> Dict[str, Any]:
        """返回工具定义，供 LLM 使用。"""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters_schema,
        }

    async def execute(self, **kwargs) -> Any:
        """执行工具函数。"""
        if inspect.iscoroutinefunction(self.func):
            return await self.func(**kwargs)
        return self.func(**kwargs)


class ToolRegistry:
    """
    全局 Tool 注册表。
    """

    _tools: Dict[str, ToolFunc] = {}

    @classmethod
    def register(
        cls,
        tool: Optional[ToolFunc | Callable] = None,
        *,
        name: Optional[str] = None,
        description: str = "",
        parameters_schema: Optional[Dict[str, Any]] = None,
    ):
        """
        注册一个工具函数。

        用法：
            # 装饰器（推荐）
            @register_tool(name="my_tool", description="...")
            def my_tool(arg: str) -> str:
                return ...

            # 直接注册
            tool_func = ToolFunc(my_func, name="my_tool")
            registry.register(tool_func)
        """
        def _do_register(fn: Callable) -> Callable:
            tool_name = name or getattr(fn, "_tool_name", None) or fn.__name__
            tool_desc = description or getattr(fn, "_tool_description", "") or (fn.__doc__ or "")
            tool_schema = parameters_schema or getattr(fn, "_tool_schema", None)

            if tool_name in cls._tools:
                logger.warning(f"Tool '{tool_name}' already registered, overwriting")
            cls._tools[tool_name] = ToolFunc(
                func=fn,
                name=tool_name,
                description=tool_desc,
                parameters_schema=tool_schema,
            )
            logger.info(f"[ToolRegistry] Registered tool: {tool_name}")
            return fn

        if tool is None:
            return _do_register
        elif isinstance(tool, ToolFunc):
            tool_name = name or tool.name
            cls._tools[tool_name] = tool
            return tool
        else:
            return _do_register(tool)

    @classmethod
    def get(cls, name: str) -> Optional[ToolFunc]:
        """按名称获取 ToolFunc。"""
        return cls._tools.get(name)

    @classmethod
    def list_tools(cls) -> list[str]:
        """列出所有已注册的 Tool 名称。"""
        return list(cls._tools.keys())

    @classmethod
    def get_all_schemas(cls) -> list[Dict[str, Any]]:
        """获取所有工具的 LLM 调用定义。"""
        return [tf.get_schema() for tf in cls._tools.values()]

    @classmethod
    def discover(cls, package: str):
        """
        自动发现并注册包内的所有 @register_tool 装饰的函数。

        用法：
            registry.discover("app.tools")
        """
        import importlib

        try:
            mod = importlib.import_module(package)
        except ImportError as e:
            logger.warning(f"Cannot import tool package '{package}': {e}")
            return

        for attr_name in dir(mod):
            attr = getattr(mod, attr_name)
            if callable(attr) and hasattr(attr, "_tool_name"):
                tool_name = getattr(attr, "_tool_name") or attr_name
                if tool_name in cls._tools:
                    continue
                cls._tools[tool_name] = ToolFunc(
                    func=attr,
                    name=tool_name,
                    description=getattr(attr, "_tool_description", "") or (attr.__doc__ or ""),
                    parameters_schema=getattr(attr, "_tool_schema", None),
                )
                logger.info(f"[ToolRegistry] Discovered tool: {tool_name}")


def register_tool(
    name: Optional[str] = None,
    description: str = "",
    parameters_schema: Optional[Dict[str, Any]] = None,
) -> Callable:
    """
    工具注册装饰器。

    用法：
        @register_tool(name="my_tool", description="...")
        def my_tool(arg: str) -> str:
            return ...
    """
    def decorator(fn: Callable) -> Callable:
        fn._tool_name = name
        fn._tool_description = description
        fn._tool_schema = parameters_schema
        ToolRegistry.register(
            fn,
            name=name,
            description=description,
            parameters_schema=parameters_schema,
        )
        return fn
    return decorator


def get_tool_registry() -> type[ToolRegistry]:
    return ToolRegistry
