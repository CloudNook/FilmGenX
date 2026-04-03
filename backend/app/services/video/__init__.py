# 视频服务模块
# 负责视频片段生成、处理与合成相关的所有能力。
#
#   generator.py        - 视频生成（Kling AI / Runway Gen-3 API 封装），将图片转化为动态镜头
#   compositor.py       - 视频合成（按分镜顺序拼接片段、添加转场效果）
#   effects.py          - 特效叠加（斗气粒子、火焰、光效等后期特效层合成）
#   color_grading.py    - 色彩分级（根据场景类型应用对应色调预设）
#   subtitle.py         - 字幕生成与烧录（支持样式配置）
