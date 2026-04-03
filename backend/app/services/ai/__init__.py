# AI 服务模块
# 封装所有与 AI 模型交互的能力，对上层 Service 屏蔽具体模型差异。
#
#   llm_service.py          - 大语言模型调用（Claude/GPT），用于高光选取、分镜脚本生成
#   image_service.py        - 图像生成（Stable Diffusion / MidJourney API），用于单镜头图片生成
#   consistency_service.py  - 角色一致性控制（IP-Adapter / LoRA 参数管理）
#   prompt_builder.py       - 提示词构建器（将分镜JSON结构转化为图像生成提示词）
#   visual_bible.py         - 世界观视觉规范数据（斗气颜色、势力色调等常量与查询）
