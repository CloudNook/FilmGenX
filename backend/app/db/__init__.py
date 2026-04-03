# 数据库模块
# 管理 PostgreSQL 连接池、会话生命周期和数据库迁移。
#
#   session.py          - SQLAlchemy 异步引擎和 Session 工厂（AsyncSession）
#   base.py             - ORM 基类（所有 Model 的父类，含 id/created_at/updated_at 公共字段）
#   migrations/         - Alembic 数据库迁移脚本目录
