# Stores（Pinia 状态管理）

每个 store 管理一个业务域的全局状态，使用 Pinia Composition API 风格。

| 文件 | 说明 |
|------|------|
| `projectStore.ts` | 当前项目信息、生产进度 |
| `sceneStore.ts` | 高光片段列表、当前选中片段 |
| `storyboardStore.ts` | 分镜脚本数据、时间轴排序 |
| `shotStore.ts` | 当前编辑的镜头数据、依赖关系图 |
| `characterStore.ts` | 角色列表、当前选中版本 |
| `assetStore.ts` | 素材库、上传队列 |
| `taskStore.ts` | 全局任务队列状态（轮询进行中的AI生成任务）|
| `uiStore.ts` | UI 状态（侧边栏折叠、主题、当前活跃面板）|
