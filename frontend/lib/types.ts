// FilmGenX 类型定义

// 用户相关
export interface User {
  id: string;
  name: string;
  email: string;
  avatar?: string;
  role: 'admin' | 'editor' | 'viewer';
}

// 项目相关
export interface Project {
  id: string;
  name: string;
  description: string;
  coverImage?: string;
  status: 'draft' | 'in_progress' | 'completed' | 'archived';
  createdAt: string;
  updatedAt: string;
  episodeCount: number;
  shotCount: number;
  progress: number;
  tags: string[];
}

// 分集相关
export interface Episode {
  id: string;
  projectId: string;
  number: number;
  title: string;
  synopsis: string;
  status: 'draft' | 'scripting' | 'storyboarding' | 'production' | 'completed';
  duration: number; // 秒
  shotCount: number;
  completedShots: number;
  createdAt: string;
  updatedAt: string;
}

// 分镜/镜头相关
export interface Shot {
  id: string;
  episodeId: string;
  number: number;
  description: string;
  dialogue?: string;
  duration: number; // 秒
  cameraAngle: CameraAngle;
  shotType: ShotType;
  characters: string[];
  location: string;
  mood: string;
  status: 'draft' | 'approved' | 'rendering' | 'completed';
  thumbnailUrl?: string;
  videoUrl?: string;
  audioUrl?: string;
  version: number;
  versions: ShotVersion[];
}

export interface ShotVersion {
  id: string;
  version: number;
  thumbnailUrl?: string;
  videoUrl?: string;
  createdAt: string;
  note?: string;
}

export type CameraAngle = 
  | 'eye_level' 
  | 'high_angle' 
  | 'low_angle' 
  | 'birds_eye' 
  | 'dutch_angle'
  | 'over_shoulder';

export type ShotType = 
  | 'extreme_wide' 
  | 'wide' 
  | 'medium_wide' 
  | 'medium' 
  | 'medium_close' 
  | 'close_up' 
  | 'extreme_close_up';

// 角色相关
export interface Character {
  id: string;
  projectId: string;
  name: string;
  description: string;
  personality: string;
  appearance: string;
  avatarUrl?: string;
  referenceImages: string[];
  voiceStyle?: string;
  age?: number;
  role: 'protagonist' | 'antagonist' | 'supporting' | 'background';
}

// 对话消息
export interface Message {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: string;
  attachments?: Attachment[];
  metadata?: {
    type?: 'script' | 'shot' | 'character' | 'general';
    relatedId?: string;
  };
}

export interface Attachment {
  id: string;
  type: 'image' | 'video' | 'audio' | 'document';
  url: string;
  name: string;
  size: number;
}

// 对话会话
export interface Conversation {
  id: string;
  projectId: string;
  episodeId?: string;
  title: string;
  messages: Message[];
  createdAt: string;
  updatedAt: string;
}

// 视频制作相关
export interface VideoTask {
  id: string;
  shotId: string;
  type: 'render' | 'composite' | 'audio_sync' | 'export';
  status: 'queued' | 'processing' | 'completed' | 'failed';
  progress: number;
  startedAt?: string;
  completedAt?: string;
  error?: string;
}

// 时间线
export interface TimelineItem {
  id: string;
  shotId: string;
  startTime: number;
  endTime: number;
  layer: number;
}

// 全局设置
export interface GlobalSettings {
  defaultResolution: '720p' | '1080p' | '2k' | '4k';
  defaultFrameRate: 24 | 30 | 60;
  defaultAspectRatio: '16:9' | '4:3' | '21:9' | '1:1';
  aiModel: string;
  voiceModel: string;
  autoSave: boolean;
  autoSaveInterval: number; // 分钟
  language: 'zh-CN' | 'en-US';
  theme: 'dark' | 'light' | 'system';
}

// 情感曲线数据点
export interface EmotionPoint {
  time: number;
  tension: number;
  emotion: 'joy' | 'sadness' | 'anger' | 'fear' | 'surprise' | 'neutral';
  label?: string;
}

// 导航项
export interface NavItem {
  title: string;
  href: string;
  icon?: string;
  badge?: number;
  children?: NavItem[];
}
