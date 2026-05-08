# 数据库模型层（ORM）
# 此文件统一导入所有模型，确保 Alembic 迁移时能自动发现所有表。

from app.models.asset import Asset
from app.models.project import Project
from app.models.skill import Skill
from app.models.supervisor_event import SupervisorEvent
from app.models.supervisor_workflow import SupervisorWorkflow
from app.models.supervisor_workflow_node import (
    SupervisorWorkflowNode,
    SupervisorWorkflowNodeDependency,
)
from app.models.user import User
from app.models.workspace import Workspace

__all__ = [
    "Asset",
    "Project",
    "Skill",
    "SupervisorEvent",
    "SupervisorWorkflow",
    "SupervisorWorkflowNode",
    "SupervisorWorkflowNodeDependency",
    "User",
    "Workspace",
]
