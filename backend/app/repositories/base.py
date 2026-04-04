"""
Repository 基类。

提供通用的 CRUD 操作，各模块 Repository 继承并扩展业务方法。
所有查询自动过滤软删除记录（is_deleted=False）。
"""

from typing import Any, Dict, Generic, List, Optional, Type, TypeVar

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import Base

ModelT = TypeVar("ModelT", bound=Base)


class BaseRepository(Generic[ModelT]):
    """通用异步 Repository，封装增删改查基础操作。"""

    def __init__(self, model: Type[ModelT], session: AsyncSession) -> None:
        self.model = model
        self.session = session

    async def get(self, id: int) -> Optional[ModelT]:
        """按主键查询单条记录（已过滤软删除）。"""
        result = await self.session.execute(
            select(self.model).where(
                self.model.id == id,
                self.model.is_deleted.is_(False),
            )
        )
        return result.scalar_one_or_none()

    async def list(
        self,
        *,
        filters: Optional[List[Any]] = None,
        order_by: Optional[Any] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[List[ModelT], int]:
        """分页查询列表，返回 (items, total)。

        Args:
            filters:   额外过滤条件，如 [Model.project_id == 1]。
            order_by:  排序条件，默认按 id 升序。
            page:      当前页（从 1 开始）。
            page_size: 每页条数。
        """
        base_cond = [self.model.is_deleted.is_(False)]
        if filters:
            base_cond.extend(filters)

        # 查总数
        count_q = select(func.count()).select_from(self.model).where(*base_cond)
        total = (await self.session.execute(count_q)).scalar_one()

        # 查数据
        order = order_by if order_by is not None else self.model.id.asc()
        data_q = (
            select(self.model)
            .where(*base_cond)
            .order_by(order)
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        items = (await self.session.execute(data_q)).scalars().all()
        return list(items), total

    async def create(self, **kwargs: Any) -> ModelT:
        """创建新记录并返回。"""
        obj = self.model(**kwargs)
        self.session.add(obj)
        await self.session.flush()          # 获取数据库生成的 id，但不提交事务
        await self.session.refresh(obj)
        return obj

    async def update(self, obj: ModelT, data: Dict[str, Any]) -> ModelT:
        """更新记录字段并返回。

        Args:
            obj:  已从数据库查询的 ORM 实例。
            data: 要更新的字段字典（仅传入非 None 值）。
        """
        for key, value in data.items():
            setattr(obj, key, value)
        await self.session.flush()
        await self.session.refresh(obj)
        return obj

    async def soft_delete(self, obj: ModelT) -> None:
        """软删除：设置 is_deleted=True，不物理删除。"""
        from datetime import datetime, timezone
        obj.is_deleted = True
        obj.deleted_at = datetime.now(timezone.utc)
        await self.session.flush()
