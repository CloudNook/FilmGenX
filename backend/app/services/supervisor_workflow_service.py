"""
SupervisorWorkflow 业务逻辑层。

封装流水线记录的业务操作：
- create_workflow: 创建流水线记录
- update_status: 更新执行状态
- update_stage: 更新当前阶段
- append_artifacts: 追加产物
- get_workflow: 查询详情
- list_workflows: 分页查询
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.supervisor_workflow import SupervisorWorkflow
from app.repositories.project import ProjectRepository
from app.repositories.supervisor_workflow import SupervisorWorkflowRepository


class SupervisorWorkflowService:
    """
    SupervisorWorkflow 业务逻辑。

    负责流水线记录的创建、状态管理和产物持久化。
    """

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = SupervisorWorkflowRepository(db)

    async def create_workflow(
        self,
        project_id: int,
        owner_id: int,
        supervisor_session_id: str,
        user_request: str,
        model: str = "gemini-3-flash-preview",
    ) -> SupervisorWorkflow:
        """
        创建一条新的流水线记录（初始状态 = running）。

        在 /api/v1/supervisor/stream 入口处调用。
        """
        # 权限校验：确保 project 属于该用户
        project_repo = ProjectRepository(self.db)
        project = await project_repo.get_by_id_and_owner(project_id, owner_id)
        if not project:
            from fastapi import HTTPException, status
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="项目不存在或无权访问",
            )

        workflow = await self.repo.create(
            project_id=project_id,
            owner_id=owner_id,
            supervisor_session_id=supervisor_session_id,
            user_request=user_request,
            model=model,
            status="running",
        )
        await self.db.commit()
        await self.db.refresh(workflow)
        return workflow

    async def update_stage(
        self,
        supervisor_session_id: str,
        stage: str,
    ) -> Optional[SupervisorWorkflow]:
        """
        更新当前流水线阶段。

        阶段值：outline_writer | script_writer | storyboarder
        """
        workflow = await self.repo.get_by_session_id(supervisor_session_id)
        if not workflow:
            return None
        workflow.current_stage = stage
        await self.db.commit()
        await self.db.refresh(workflow)
        return workflow

    async def increment_loop_count(
        self,
        supervisor_session_id: str,
    ) -> Optional[int]:
        """
        递增 loop_count，返回更新后的值。
        """
        workflow = await self.repo.get_by_session_id(supervisor_session_id)
        if not workflow:
            return None
        workflow.loop_count = (workflow.loop_count or 0) + 1
        await self.db.commit()
        return workflow.loop_count

    async def update_tokens(
        self,
        supervisor_session_id: str,
        tokens_used: int,
    ) -> Optional[SupervisorWorkflow]:
        """累加 token 消耗。"""
        workflow = await self.repo.get_by_session_id(supervisor_session_id)
        if not workflow:
            return None
        workflow.total_tokens = (workflow.total_tokens or 0) + tokens_used
        await self.db.commit()
        await self.db.refresh(workflow)
        return workflow

    async def append_artifacts(
        self,
        supervisor_session_id: str,
        stage: str,
        artifact: Dict[str, Any],
    ) -> Optional[SupervisorWorkflow]:
        """
        追加阶段产物到 artifacts JSON。

        artifacts 结构：{"outline_writer": {...}, "script_writer": {...}, "storyboarder": {...}}
        """
        workflow = await self.repo.get_by_session_id(supervisor_session_id)
        if not workflow:
            return None

        if workflow.artifacts is None:
            workflow.artifacts = {}
        workflow.artifacts[stage] = artifact
        workflow.current_stage = stage
        await self.db.commit()
        await self.db.refresh(workflow)
        return workflow

    async def mark_completed(
        self,
        supervisor_session_id: str,
        final_result: Optional[str] = None,
    ) -> Optional[SupervisorWorkflow]:
        """标记流水线完成。"""
        workflow = await self.repo.get_by_session_id(supervisor_session_id)
        if not workflow:
            return None
        return await self.repo.mark_completed(
            workflow,
            artifacts=workflow.artifacts,
            final_result=final_result,
        )

    async def mark_failed(
        self,
        supervisor_session_id: str,
        error_message: str,
    ) -> Optional[SupervisorWorkflow]:
        """标记流水线失败。"""
        workflow = await self.repo.get_by_session_id(supervisor_session_id)
        if not workflow:
            return None
        return await self.repo.mark_failed(workflow, error_message)

    async def get_workflow(
        self,
        workflow_id: int,
        project_id: int,
    ) -> Optional[SupervisorWorkflow]:
        """按 ID + project_id 查询，用于 GET /{id} 端点。"""
        return await self.repo.get_by_id_and_project(workflow_id, project_id)

    async def get_workflow_by_session(
        self,
        supervisor_session_id: str,
    ) -> Optional[SupervisorWorkflow]:
        """按 supervisor_session_id 查询。"""
        return await self.repo.get_by_session_id(supervisor_session_id)

    async def list_workflows(
        self,
        project_id: int,
        owner_id: int,
        *,
        page: int = 1,
        page_size: int = 20,
        status: Optional[str] = None,
    ) -> Tuple[List[SupervisorWorkflow], int]:
        """分页查询项目下的流水线记录。"""
        # 权限校验
        project_repo = ProjectRepository(self.db)
        project = await project_repo.get_by_id_and_owner(project_id, owner_id)
        if not project:
            from fastapi import HTTPException, status
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="项目不存在或无权访问",
            )
        return await self.repo.list_by_project(
            project_id,
            page=page,
            page_size=page_size,
            status=status,
        )
