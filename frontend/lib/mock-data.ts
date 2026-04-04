import type {
  User,
  Project,
  Episode,
  Shot,
  Character,
  Message,
  Conversation,
  GlobalSettings,
  EmotionPoint,
} from './types';

// 当前用户
export const currentUser: User = {
  id: 'user-1',
  name: '张导演',
  email: 'zhang@filmgenx.com',
  avatar: '/avatars/user-1.jpg',
  role: 'admin',
};

// 项目列表
export const projects: Project[] = [
  {
    id: 'proj-1',
    name: '星际迷航：新纪元',
    description: '一部讲述人类首次星际殖民的科幻动画剧集，展现未来人类在宇宙中的冒险与探索。',
    coverImage: '/covers/project-1.jpg',
    status: 'in_progress',
    createdAt: '2024-01-15T10:00:00Z',
    updatedAt: '2024-03-20T15:30:00Z',
    episodeCount: 12,
    shotCount: 480,
    progress: 65,
    tags: ['科幻', '冒险', '太空'],
  },
  {
    id: 'proj-2',
    name: '江南往事',
    description: '发生在民国时期江南水乡的爱情故事，讲述两个家族之间的恩怨情仇。',
    coverImage: '/covers/project-2.jpg',
    status: 'in_progress',
    createdAt: '2024-02-01T09:00:00Z',
    updatedAt: '2024-03-19T11:20:00Z',
    episodeCount: 24,
    shotCount: 960,
    progress: 35,
    tags: ['爱情', '历史', '民国'],
  },
  {
    id: 'proj-3',
    name: '魔法学院日记',
    description: '青少年奇幻动画，讲述一群少年在魔法学院的成长故事。',
    coverImage: '/covers/project-3.jpg',
    status: 'draft',
    createdAt: '2024-03-10T14:00:00Z',
    updatedAt: '2024-03-18T16:45:00Z',
    episodeCount: 0,
    shotCount: 0,
    progress: 0,
    tags: ['奇幻', '校园', '青少年'],
  },
  {
    id: 'proj-4',
    name: '都市夜行者',
    description: '现代都市悬疑动画，讲述一位私家侦探在夜晚城市中追查真相的故事。',
    coverImage: '/covers/project-4.jpg',
    status: 'completed',
    createdAt: '2023-06-01T08:00:00Z',
    updatedAt: '2024-01-10T10:00:00Z',
    episodeCount: 8,
    shotCount: 320,
    progress: 100,
    tags: ['悬疑', '都市', '动作'],
  },
];

// 分集数据
export const episodes: Episode[] = [
  {
    id: 'ep-1',
    projectId: 'proj-1',
    number: 1,
    title: '启航',
    synopsis: '人类首艘星际飞船"曙光号"即将启航，船长陈明和他的团队面临着未知的挑战。',
    status: 'completed',
    duration: 1440,
    shotCount: 45,
    completedShots: 45,
    createdAt: '2024-01-20T10:00:00Z',
    updatedAt: '2024-02-15T12:00:00Z',
  },
  {
    id: 'ep-2',
    projectId: 'proj-1',
    number: 2,
    title: '虫洞之谜',
    synopsis: '飞船意外遭遇虫洞，被传送到了银河系边缘的未知星域。',
    status: 'completed',
    duration: 1380,
    shotCount: 42,
    completedShots: 42,
    createdAt: '2024-02-01T10:00:00Z',
    updatedAt: '2024-02-28T14:00:00Z',
  },
  {
    id: 'ep-3',
    projectId: 'proj-1',
    number: 3,
    title: '第一次接触',
    synopsis: '船员们在一颗神秘行星上发现了外星文明的痕迹。',
    status: 'production',
    duration: 1500,
    shotCount: 48,
    completedShots: 36,
    createdAt: '2024-02-15T10:00:00Z',
    updatedAt: '2024-03-20T09:00:00Z',
  },
  {
    id: 'ep-4',
    projectId: 'proj-1',
    number: 4,
    title: '信任危机',
    synopsis: '飞船内部出现分歧，部分船员质疑继续探索的决定。',
    status: 'storyboarding',
    duration: 1320,
    shotCount: 40,
    completedShots: 12,
    createdAt: '2024-03-01T10:00:00Z',
    updatedAt: '2024-03-19T16:00:00Z',
  },
  {
    id: 'ep-5',
    projectId: 'proj-1',
    number: 5,
    title: '黑暗星云',
    synopsis: '穿越一片危险的黑暗星云，飞船遭遇了前所未有的挑战。',
    status: 'scripting',
    duration: 0,
    shotCount: 0,
    completedShots: 0,
    createdAt: '2024-03-15T10:00:00Z',
    updatedAt: '2024-03-18T11:00:00Z',
  },
];

// 镜头数据
export const shots: Shot[] = [
  {
    id: 'shot-1',
    episodeId: 'ep-3',
    number: 1,
    description: '飞船从太空中缓缓下降，接近神秘行星的大气层。',
    duration: 8,
    cameraAngle: 'high_angle',
    shotType: 'extreme_wide',
    characters: [],
    location: '太空/行星轨道',
    mood: '神秘、壮观',
    status: 'completed',
    thumbnailUrl: '/shots/shot-1-thumb.jpg',
    videoUrl: '/shots/shot-1.mp4',
    version: 3,
    versions: [
      { id: 'v1', version: 1, thumbnailUrl: '/shots/shot-1-v1.jpg', createdAt: '2024-03-01T10:00:00Z', note: '初版' },
      { id: 'v2', version: 2, thumbnailUrl: '/shots/shot-1-v2.jpg', createdAt: '2024-03-05T14:00:00Z', note: '调整色彩' },
      { id: 'v3', version: 3, thumbnailUrl: '/shots/shot-1-v3.jpg', createdAt: '2024-03-10T09:00:00Z', note: '最终版' },
    ],
  },
  {
    id: 'shot-2',
    episodeId: 'ep-3',
    number: 2,
    description: '船长陈明站在驾驶舱窗前，凝视着下方的行星表面。',
    dialogue: '陈明：这就是我们要寻找的答案吗？',
    duration: 5,
    cameraAngle: 'over_shoulder',
    shotType: 'medium',
    characters: ['char-1'],
    location: '曙光号驾驶舱',
    mood: '沉思、期待',
    status: 'completed',
    thumbnailUrl: '/shots/shot-2-thumb.jpg',
    videoUrl: '/shots/shot-2.mp4',
    version: 2,
    versions: [
      { id: 'v1', version: 1, thumbnailUrl: '/shots/shot-2-v1.jpg', createdAt: '2024-03-02T11:00:00Z', note: '初版' },
      { id: 'v2', version: 2, thumbnailUrl: '/shots/shot-2-v2.jpg', createdAt: '2024-03-08T15:00:00Z', note: '调整表情' },
    ],
  },
  {
    id: 'shot-3',
    episodeId: 'ep-3',
    number: 3,
    description: '科学官李薇在控制台前分析行星数据。',
    dialogue: '李薇：大气成分显示这颗行星适合人类居住，但是...',
    duration: 6,
    cameraAngle: 'eye_level',
    shotType: 'medium_close',
    characters: ['char-2'],
    location: '曙光号科学实验室',
    mood: '专注、疑惑',
    status: 'completed',
    thumbnailUrl: '/shots/shot-3-thumb.jpg',
    version: 1,
    versions: [
      { id: 'v1', version: 1, thumbnailUrl: '/shots/shot-3-v1.jpg', createdAt: '2024-03-04T10:00:00Z', note: '初版' },
    ],
  },
  {
    id: 'shot-4',
    episodeId: 'ep-3',
    number: 4,
    description: '飞船降落在行星表面，掀起一片尘土。',
    duration: 10,
    cameraAngle: 'low_angle',
    shotType: 'wide',
    characters: [],
    location: '神秘行星表面',
    mood: '震撼、紧张',
    status: 'rendering',
    thumbnailUrl: '/shots/shot-4-thumb.jpg',
    version: 1,
    versions: [
      { id: 'v1', version: 1, thumbnailUrl: '/shots/shot-4-v1.jpg', createdAt: '2024-03-15T09:00:00Z', note: '渲染中' },
    ],
  },
  {
    id: 'shot-5',
    episodeId: 'ep-3',
    number: 5,
    description: '船员们穿着太空服走出飞船，踏上陌生的土地。',
    duration: 8,
    cameraAngle: 'eye_level',
    shotType: 'medium_wide',
    characters: ['char-1', 'char-2', 'char-3'],
    location: '神秘行星表面',
    mood: '激动、谨慎',
    status: 'approved',
    version: 1,
    versions: [],
  },
  {
    id: 'shot-6',
    episodeId: 'ep-3',
    number: 6,
    description: '安全官王刚手持扫描仪，检测周围环境。',
    dialogue: '王刚：目前没有检测到威胁，但保持警惕。',
    duration: 4,
    cameraAngle: 'eye_level',
    shotType: 'close_up',
    characters: ['char-3'],
    location: '神秘行星表面',
    mood: '警觉、专业',
    status: 'draft',
    version: 1,
    versions: [],
  },
];

// 角色数据
export const characters: Character[] = [
  {
    id: 'char-1',
    projectId: 'proj-1',
    name: '陈明',
    description: '曙光号船长，经验丰富的星际探险家。',
    personality: '冷静、果断、富有责任感，但内心深处隐藏着对家人的思念。',
    appearance: '40岁左右，身材高大，短发，眼神深邃，总是穿着整洁的舰长制服。',
    avatarUrl: '/characters/chen-ming.jpg',
    referenceImages: ['/characters/chen-ming-ref-1.jpg', '/characters/chen-ming-ref-2.jpg'],
    voiceStyle: '低沉、沉稳',
    age: 42,
    role: 'protagonist',
  },
  {
    id: 'char-2',
    projectId: 'proj-1',
    name: '李薇',
    description: '首席科学官，天体物理学专家。',
    personality: '聪明、好奇、有时过于专注于研究而忽略周围的危险。',
    appearance: '32岁，长发扎成马尾，戴着智能眼镜，经常穿白色实验服。',
    avatarUrl: '/characters/li-wei.jpg',
    referenceImages: ['/characters/li-wei-ref-1.jpg'],
    voiceStyle: '清亮、快速',
    age: 32,
    role: 'supporting',
  },
  {
    id: 'char-3',
    projectId: 'proj-1',
    name: '王刚',
    description: '安全官，前军方特种部队成员。',
    personality: '警觉、忠诚、沉默寡言，但在关键时刻总能挺身而出。',
    appearance: '38岁，肌肉发达，面部有一道疤痕，总是穿着战术装备。',
    avatarUrl: '/characters/wang-gang.jpg',
    referenceImages: [],
    voiceStyle: '粗犷、简洁',
    age: 38,
    role: 'supporting',
  },
  {
    id: 'char-4',
    projectId: 'proj-1',
    name: '小艾',
    description: '飞船AI助手，负责船舶系统管理。',
    personality: '理性、幽默、偶尔展现出类人的情感反应。',
    appearance: '以全息投影形式出现，通常显示为蓝色光球或人形轮廓。',
    avatarUrl: '/characters/xiao-ai.jpg',
    referenceImages: [],
    voiceStyle: '电子音、温和',
    role: 'supporting',
  },
];

// 对话数据
export const conversations: Conversation[] = [
  {
    id: 'conv-1',
    projectId: 'proj-1',
    episodeId: 'ep-3',
    title: '第三集剧本讨论',
    messages: [
      {
        id: 'msg-1',
        role: 'user',
        content: '我想让第三集的开场更加震撼，现在的版本感觉有点平淡。',
        timestamp: '2024-03-18T10:30:00Z',
      },
      {
        id: 'msg-2',
        role: 'assistant',
        content: '我理解您的需求。建议我们可以从以下几个方面增强开场的震撼感：\n\n1. **视觉冲击**：将飞船进入大气层的镜头延长，增加大气摩擦产生的火焰效果\n2. **音乐配合**：使用紧张的弦乐渐进式推进\n3. **角色反应**：加入船员们紧握座椅、交换紧张眼神的镜头\n\n您觉得哪个方向更符合您的预期？',
        timestamp: '2024-03-18T10:31:00Z',
      },
      {
        id: 'msg-3',
        role: 'user',
        content: '我喜欢第一个建议，可以帮我重新设计这个镜头吗？',
        timestamp: '2024-03-18T10:35:00Z',
      },
      {
        id: 'msg-4',
        role: 'assistant',
        content: '好的，我已经为您重新设计了开场镜头：\n\n**镜头1-A（修改版）**\n- 时长：12秒（原8秒）\n- 开始：远景，飞船从太空中逼近行星\n- 中段：切换到飞船视角，大气层开始出现橙红色火焰\n- 结束：火焰包裹整个画面，过渡到下一镜头\n\n我可以立即生成这个镜头的预览，您需要吗？',
        timestamp: '2024-03-18T10:36:00Z',
        metadata: {
          type: 'shot',
          relatedId: 'shot-1',
        },
      },
    ],
    createdAt: '2024-03-18T10:30:00Z',
    updatedAt: '2024-03-18T10:36:00Z',
  },
];

// 全局设置
export const globalSettings: GlobalSettings = {
  defaultResolution: '1080p',
  defaultFrameRate: 24,
  defaultAspectRatio: '16:9',
  aiModel: 'FilmGenX-v2',
  voiceModel: 'VoiceGen-Pro',
  autoSave: true,
  autoSaveInterval: 5,
  language: 'zh-CN',
  theme: 'dark',
};

// 情感曲线数据
export const emotionCurveData: EmotionPoint[] = [
  { time: 0, tension: 30, emotion: 'neutral', label: '开场' },
  { time: 60, tension: 45, emotion: 'surprise', label: '发现行星' },
  { time: 120, tension: 60, emotion: 'fear', label: '进入大气层' },
  { time: 180, tension: 50, emotion: 'joy', label: '成功着陆' },
  { time: 240, tension: 40, emotion: 'neutral', label: '探索准备' },
  { time: 300, tension: 55, emotion: 'surprise', label: '发现遗迹' },
  { time: 360, tension: 75, emotion: 'fear', label: '未知信号' },
  { time: 420, tension: 85, emotion: 'anger', label: '冲突爆发' },
  { time: 480, tension: 70, emotion: 'sadness', label: '损失' },
  { time: 540, tension: 60, emotion: 'neutral', label: '重整旗鼓' },
  { time: 600, tension: 80, emotion: 'surprise', label: '真相揭示' },
  { time: 660, tension: 90, emotion: 'fear', label: '最终危机' },
  { time: 720, tension: 40, emotion: 'joy', label: '解决与希望' },
];

// 辅助函数
export function getProjectById(id: string): Project | undefined {
  return projects.find(p => p.id === id);
}

export function getEpisodesByProjectId(projectId: string): Episode[] {
  return episodes.filter(e => e.projectId === projectId);
}

export function getEpisodeById(id: string): Episode | undefined {
  return episodes.find(e => e.id === id);
}

export function getShotsByEpisodeId(episodeId: string): Shot[] {
  return shots.filter(s => s.episodeId === episodeId);
}

export function getShotById(id: string): Shot | undefined {
  return shots.find(s => s.id === id);
}

export function getCharactersByProjectId(projectId: string): Character[] {
  return characters.filter(c => c.projectId === projectId);
}

export function getCharacterById(id: string): Character | undefined {
  return characters.find(c => c.id === id);
}

export function getConversationsByProjectId(projectId: string): Conversation[] {
  return conversations.filter(c => c.projectId === projectId);
}
