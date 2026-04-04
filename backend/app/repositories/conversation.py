"""
Conversation 和 Message Repository。
"""

from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.conversation import Conversation, Message
from app.repositories.base import BaseRepository


class ConversationRepository(BaseRepository[Conversation]):

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Conversation, session)

    async def get_by_project(
        self,
        project_id: int,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[List[Conversation], int]:
        """获取项目下的会话列表（不含消息，按最新更新排序）。"""
        return await self.list(
            filters=[Conversation.project_id == project_id],
            order_by=Conversation.updated_at.desc(),
            page=page,
            page_size=page_size,
        )

    async def get_with_messages(self, conversation_id: int) -> Optional[Conversation]:
        """获取会话详情，预加载全部消息（按 seq 升序）。"""
        result = await self.session.execute(
            select(Conversation)
            .where(
                Conversation.id == conversation_id,
                Conversation.is_deleted.is_(False),
            )
            .options(selectinload(Conversation.messages))
        )
        return result.scalar_one_or_none()

    async def get_by_id_and_project(
        self, conversation_id: int, project_id: int
    ) -> Optional[Conversation]:
        result = await self.session.execute(
            select(Conversation).where(
                Conversation.id == conversation_id,
                Conversation.project_id == project_id,
                Conversation.is_deleted.is_(False),
            )
        )
        return result.scalar_one_or_none()


class MessageRepository(BaseRepository[Message]):

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Message, session)

    async def get_next_seq(self, conversation_id: int) -> int:
        """获取会话中下一条消息的序号。"""
        from sqlalchemy import func
        result = await self.session.execute(
            select(func.coalesce(func.max(Message.seq), -1)).where(
                Message.conversation_id == conversation_id,
                Message.is_deleted.is_(False),
            )
        )
        return result.scalar_one() + 1

    async def create_message(
        self,
        conversation_id: int,
        role: str,
        type: str,
        content: str,
        outline_data: Optional[dict] = None,
    ) -> Message:
        """创建消息，自动计算 seq。"""
        seq = await self.get_next_seq(conversation_id)
        return await self.create(
            conversation_id=conversation_id,
            role=role,
            type=type,
            content=content,
            outline_data=outline_data,
            seq=seq,
        )

    async def get_by_conversation(self, conversation_id: int) -> List[Message]:
        """获取会话的所有消息，按 seq 升序。"""
        result = await self.session.execute(
            select(Message)
            .where(
                Message.conversation_id == conversation_id,
                Message.is_deleted.is_(False),
            )
            .order_by(Message.seq.asc())
        )
        return list(result.scalars().all())
