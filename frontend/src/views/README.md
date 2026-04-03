# Views（页面视图）

每个文件对应一个路由页面，仅负责页面布局与组件组合，不含业务逻辑。

| 文件 | 路由 | 说明 |
|------|------|------|
| `HomeView.vue` | `/` | 项目列表首页 |
| `ProjectView.vue` | `/project/:id` | 项目详情，生产进度总览 |
| `SceneView.vue` | `/project/:id/scenes` | 高光片段管理，AI选取与评分 |
| `StoryboardView.vue` | `/project/:id/storyboard/:sid` | 分镜脚本编辑器 |
| `ShotView.vue` | `/project/:id/shot/:shotId` | 单镜头详情与生成控制 |
| `CharacterView.vue` | `/characters` | 角色资产库管理 |
| `AssetView.vue` | `/assets` | 全局素材库 |
| `ExportView.vue` | `/project/:id/export` | 视频导出与预览 |
| `QCView.vue` | `/project/:id/qc` | 质量审核看板 |
