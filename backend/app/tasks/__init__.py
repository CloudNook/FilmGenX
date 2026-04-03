# 异步任务模块（Celery）
# 所有耗时的 AI 生成操作均以异步任务方式执行，避免 API 超时。
# 使用 Celery + Redis 作为任务队列和结果后端。
#
#   celery_app.py       - Celery 实例配置与初始化
#   scene_tasks.py      - 高光片段 AI 分析与评分任务
#   storyboard_tasks.py - 分镜脚本批量生成任务
#   shot_tasks.py       - 单镜头图像生成任务（支持并发批量）
#   video_tasks.py      - 视频生成、合成、导出任务
#   audio_tasks.py      - 配音、音效、BGM 生成任务
#   qc_tasks.py         - 质量审核自动化检测任务
