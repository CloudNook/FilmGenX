"""
Schema 公共基类。

所有响应 Schema 继承 BaseResponse，统一包含 id / created_at / updated_at。
"""

from datetime import datetime
from typing import Generic, List, Optional, TypeVar

from pydantic import BaseModel, ConfigDict

DataT = TypeVar("DataT")


class BaseResponse(BaseModel):
    """所有从数据库读取的资源响应模型的基类，自动映射 ORM 对象属性。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime


class PageResponse(BaseModel, Generic[DataT]):
    """通用分页响应体。"""

    items: List[DataT]
    total: int       # 总记录数
    page: int        # 当前页（从 1 开始）
    page_size: int   # 每页条数
