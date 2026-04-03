# 数据访问层（Repository Pattern）
# 封装所有数据库读写操作，Service 层通过 Repository 访问数据，不直接写 SQL。
# 每个 Repository 对应一张核心表，提供 CRUD 和常用查询方法。
#
#   base.py             - BaseRepository（通用 CRUD 泛型基类）
#   project_repo.py     - ProjectRepository
#   scene_repo.py       - SceneRepository（含按评分排序、按类型筛选等查询）
#   storyboard_repo.py  - StoryboardRepository
#   shot_repo.py        - ShotRepository（含依赖关系查询、按场景批量获取）
#   character_repo.py   - CharacterRepository + CharacterVersionRepository
#   asset_repo.py       - AssetRepository（含按类型、按标签检索）
#   task_repo.py        - GenerationTaskRepository（含状态更新、超时检测）
#   prompt_repo.py      - PromptTemplateRepository（含版本历史查询）
