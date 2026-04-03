# 音频服务模块
# 负责语音合成、音效匹配和背景音乐编排。
#
#   tts_service.py      - AI 配音（Azure TTS / ElevenLabs），根据台词情感标注生成语音
#   sfx_service.py      - 音效管理（音效库查询、自动匹配触发点）
#   bgm_service.py      - 背景音乐编排（根据情绪弧线选取和过渡 BGM 片段）
#   mixer.py            - 音频混合（将语音、音效、BGM 按时间轴合并为最终音轨）
