# Pydantic Schema 层（数据验证与序列化）
# 定义 API 请求体和响应体的数据结构，与 ORM 模型分离。
#
#   project.py      - ProjectCreate / ProjectResponse
#   scene.py        - SceneCreate / SceneResponse / ScoreResult
#   storyboard.py   - StoryboardCreate / StoryboardResponse
#   shot.py         - ShotCreate / ShotUpdate / ShotResponse（含完整分镜JSON结构）
#   character.py    - CharacterCreate / CharacterResponse / CharacterVersionResponse
#   asset.py        - AssetUpload / AssetResponse
#   task.py         - TaskStatusResponse（异步任务进度查询）
#   common.py       - 通用分页、排序、错误响应结构
