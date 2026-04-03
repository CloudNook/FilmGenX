# API 层（前端请求封装）

封装所有对后端 API 的请求，统一处理请求头、错误、loading 状态。

| 文件 | 说明 |
|------|------|
| `client.ts` | Axios 实例配置（baseURL、拦截器、错误处理）|
| `projects.ts` | 项目相关接口 |
| `scenes.ts` | 高光片段接口（含触发AI选取） |
| `storyboards.ts` | 分镜脚本接口（含批量生成） |
| `shots.ts` | 单镜头接口（含重新生成、审核） |
| `characters.ts` | 角色档案接口 |
| `assets.ts` | 素材上传/查询接口 |
| `tasks.ts` | 异步任务状态查询接口 |
| `exports.ts` | 视频导出接口 |
