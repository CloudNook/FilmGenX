# API Endpoints 模块
# 按业务域拆分的路由处理器：
#
#   auth.py          - 用户认证
#   projects.py      - 项目管理
#   workspaces.py    - AI 工作台
#   assets.py        - 素材库（asset_code / asset_type 通用素材表）
#   skills.py        - Admin Skill 管理
#   supervisor.py    - Supervisor 流水线（agent-driven 链路）
#   agent_schemas.py - Sub-agent 输出 Pydantic schema 暴露
