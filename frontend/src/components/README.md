# Components（组件库）

按业务域分目录，每个目录只包含该域相关的组件。

## common/         通用组件（跨业务复用）
- `AppHeader.vue`         顶部导航栏
- `AppSidebar.vue`        侧边导航
- `TaskProgressBar.vue`   AI生成任务进度条（轮询任务状态）
- `StatusBadge.vue`       状态标签（pending/generating/done/failed）
- `ConfirmDialog.vue`     确认对话框
- `ImageViewer.vue`       图片预览（支持全屏和对比）

## scene/           高光片段相关组件
- `SceneCard.vue`         片段卡片（展示评分、类型、关联角色）
- `ScorePanel.vue`        片段评分详情面板
- `SceneFilter.vue`       按类型/评分筛选栏

## storyboard/      分镜脚本相关组件
- `StoryboardTimeline.vue`   分镜时间轴（可拖拽排序）
- `EmotionCurve.vue`         情感弧线可视化图表
- `ShotCard.vue`             分镜卡片（缩略图+基本信息）
- `DependencyGraph.vue`      分镜依赖关系图（可视化关联）

## shot/            单镜头编辑组件
- `ShotEditor.vue`           分镜JSON编辑器（表单化编辑）
- `CameraSettings.vue`       摄像机参数配置（景别、运镜、角度）
- `LightingSettings.vue`     光线参数配置
- `CharacterState.vue`       镜头内角色状态选择器
- `ShotQCChecklist.vue`      镜头质量审核清单

## character/       角色资产组件
- `CharacterCard.vue`        角色卡片（展示版本列表）
- `CharacterVersionPicker.vue`  角色状态版本选择器
- `CharacterExpressionGrid.vue` 表情参考图网格

## asset/           素材管理组件
- `AssetUploader.vue`        素材上传（支持拖拽）
- `AssetGrid.vue`            素材网格浏览器
- `AssetTag.vue`             素材标签管理

## player/          播放器组件
- `VideoPlayer.vue`          视频播放器（支持分镜时间轴同步）
- `ShotCompareView.vue`      新旧版本对比播放
