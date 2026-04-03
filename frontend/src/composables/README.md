# Composables（Vue 组合式函数）

可复用的有状态逻辑，跨组件共享，不含 UI。

| 文件 | 说明 |
|------|------|
| `useTaskPolling.ts` | 轮询异步任务状态，任务完成后自动刷新数据 |
| `useShotGenerator.ts` | 触发镜头生成、监听进度、处理结果的完整流程 |
| `useAssetUpload.ts` | 文件上传（分片、进度、重试）|
| `useStoryboardOrder.ts` | 分镜拖拽排序逻辑 |
| `useCharacterVersion.ts` | 根据章节自动匹配角色状态版本 |
| `useQCChecklist.ts` | 质量审核清单状态管理与提交 |
