# 数据库模型层（ORM）
# 使用 SQLAlchemy 定义与 PostgreSQL 映射的数据表结构。
# 此文件统一导入所有模型，确保 Alembic 迁移时能自动发现所有表。

from app.models.user import User
from app.models.project import Project
from app.models.scene import Scene
from app.models.storyboard import Storyboard
from app.models.shot import Shot
from app.models.shot_group import ShotGroup
from app.models.character import Character
from app.models.location import Location
from app.models.asset import Asset
from app.models.task import GenerationTask
from app.models.prompt import PromptTemplate
from app.models.conversation import Conversation, Message
from app.models.skill import Skill
from app.models.workspace import Workspace
from app.models.supervisor_event import SupervisorEvent
from app.models.supervisor_workflow import SupervisorWorkflow
from app.models.supervisor_workflow_node import (
    SupervisorWorkflowNode,
    SupervisorWorkflowNodeDependency,
)

__all__ = [
    "User",
    "Project",
    "Scene",
    "Storyboard",
    "Shot",
    "ShotGroup",
    "Character",
    "Location",
    "Asset",
    "GenerationTask",
    "PromptTemplate",
    "Conversation",
    "Message",
    "Skill",
    "Workspace",
    "SupervisorEvent",
    "SupervisorWorkflow",
    "SupervisorWorkflowNode",
    "SupervisorWorkflowNodeDependency",
]
