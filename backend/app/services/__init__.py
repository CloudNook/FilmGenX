# 业务逻辑服务层
# 封装所有核心业务逻辑，API 层只调用 Service，不直接操作数据库或AI接口。
# 子模块按功能域拆分：
#
#   scene_service.py        - 高光片段选取与评分业务逻辑
#   storyboard_service.py   - 分镜脚本生成与管理业务逻辑
#   shot_service.py         - 单镜头创建、依赖关系解析、连续性检查
#   character_service.py    - 角色档案管理、状态版本切换
#   asset_service.py        - 素材文件存储、检索、版本管理
#   export_service.py       - 视频片段合成与导出
#
#   ai/     - 所有 AI 能力调用封装（见子目录）
#   video/  - 视频生成与处理（见子目录）
#   audio/  - 音频生成与处理（见子目录）
