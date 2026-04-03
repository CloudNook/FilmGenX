# API Endpoints 模块
# 按业务域拆分的路由处理器，每个文件对应一个资源：
#
#   scenes.py       - 高光片段管理（选取、评分、存储）
#   storyboards.py  - 分镜脚本管理（生成、编辑、版本控制）
#   shots.py        - 单镜头管理（生成、审核、重新生成）
#   characters.py   - 角色资产管理（档案、状态版本、参考图）
#   assets.py       - 通用素材管理（图片、视频片段、音频）
#   projects.py     - 项目管理（创建项目、进度跟踪）
#   tasks.py        - 异步任务状态查询（生成任务进度）
#   exports.py      - 视频导出与发布
