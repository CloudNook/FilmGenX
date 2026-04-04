'use client';

import { useState } from 'react';
import type { EpisodeOutline } from '@/lib/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Progress } from '@/components/ui/progress';
import { Separator } from '@/components/ui/separator';
import { Slider } from '@/components/ui/slider';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible';
import { Edit, Check, X, ChevronDown, Star, Clock, Film, Users } from 'lucide-react';

interface OutlineCardProps {
  outline: EpisodeOutline;
  isEditing: boolean;
  onEditStart: () => void;
  onSave: (outline: EpisodeOutline) => void;
  onCancel: () => void;
}

const scoreLabels: Record<string, string> = {
  dramatic_tension: '戏剧张力',
  visual_potential: '视觉潜力',
  emotional_resonance: '情感共鸣',
  narrative_importance: '叙事重要性',
  audience_familiarity: '观众熟知度',
};

const priorityOptions = [
  { value: 'S', label: 'S 级（最高）' },
  { value: 'A', label: 'A 级' },
  { value: 'B', label: 'B 级' },
  { value: 'C', label: 'C 级' },
];

const sceneTypeOptions = [
  'emotional_peak', 'character_introduction', 'climax', 'battle',
  'flashback', 'montage', 'dialogue_heavy', 'visual_spectacle',
];

export function OutlineCard({
  outline,
  isEditing,
  onEditStart,
  onSave,
  onCancel,
}: OutlineCardProps) {
  const [draft, setDraft] = useState<EpisodeOutline>({ ...outline });
  const [synopsisOpen, setSynopsisOpen] = useState(true);
  const [styleOpen, setStyleOpen] = useState(false);

  // Sync draft when outline changes externally
  if (!isEditing && draft !== outline) {
    setDraft({ ...outline });
  }

  const total =
    (isEditing ? draft : outline).scores.dramatic_tension +
    (isEditing ? draft : outline).scores.visual_potential +
    (isEditing ? draft : outline).scores.emotional_resonance +
    (isEditing ? draft : outline).scores.narrative_importance +
    (isEditing ? draft : outline).scores.audience_familiarity;

  const current = isEditing ? draft : outline;

  const updateDraft = (patch: Partial<EpisodeOutline>) => {
    setDraft((prev) => ({ ...prev, ...patch }));
  };

  const updateScore = (key: string, value: number) => {
    setDraft((prev) => ({
      ...prev,
      scores: { ...prev.scores, [key]: value },
    }));
  };

  return (
    <Card className="border-border">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm font-medium flex items-center gap-2">
            <Star className="h-4 w-4 text-warning" />
            大纲草稿 v{current.version}
          </CardTitle>
          {!isEditing ? (
            <Button variant="ghost" size="sm" className="h-7 text-xs" onClick={onEditStart}>
              <Edit className="h-3 w-3 mr-1" />
              编辑
            </Button>
          ) : (
            <div className="flex gap-1">
              <Button
                variant="ghost"
                size="sm"
                className="h-7 text-xs text-destructive"
                onClick={() => {
                  setDraft({ ...outline });
                  onCancel();
                }}
              >
                <X className="h-3 w-3 mr-1" />
                取消
              </Button>
              <Button
                size="sm"
                className="h-7 text-xs"
                onClick={() => onSave(draft)}
              >
                <Check className="h-3 w-3 mr-1" />
                保存
              </Button>
            </div>
          )}
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        {/* Title & Code */}
        {isEditing ? (
          <div className="grid grid-cols-2 gap-2">
            <div>
              <label className="text-[10px] text-muted-foreground uppercase tracking-wide">标题</label>
              <Input
                value={draft.title}
                onChange={(e) => updateDraft({ title: e.target.value })}
                className="h-8 text-sm mt-0.5"
              />
            </div>
            <div>
              <label className="text-[10px] text-muted-foreground uppercase tracking-wide">编号</label>
              <Input
                value={draft.episode_code}
                onChange={(e) => updateDraft({ episode_code: e.target.value })}
                className="h-8 text-sm mt-0.5"
              />
            </div>
          </div>
        ) : (
          <div>
            <p className="font-medium text-foreground">{current.title}</p>
            <p className="text-xs text-muted-foreground">{current.episode_code}</p>
          </div>
        )}

        {/* Priority & Theme */}
        {isEditing ? (
          <div className="grid grid-cols-2 gap-2">
            <div>
              <label className="text-[10px] text-muted-foreground uppercase tracking-wide">优先级</label>
              <Select value={draft.priority} onValueChange={(v) => updateDraft({ priority: v })}>
                <SelectTrigger className="h-8 text-sm mt-0.5">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {priorityOptions.map((opt) => (
                    <SelectItem key={opt.value} value={opt.value}>
                      {opt.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div>
              <label className="text-[10px] text-muted-foreground uppercase tracking-wide">主题</label>
              <Input
                value={draft.theme}
                onChange={(e) => updateDraft({ theme: e.target.value })}
                className="h-8 text-sm mt-0.5"
              />
            </div>
          </div>
        ) : (
          <div className="flex items-center gap-2">
            <Badge variant="outline">{current.priority} 级</Badge>
            <span className="text-xs text-muted-foreground">{current.theme}</span>
          </div>
        )}

        {/* Synopsis */}
        <Collapsible open={synopsisOpen} onOpenChange={setSynopsisOpen}>
          <CollapsibleTrigger className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground w-full">
            <ChevronDown className={`h-3 w-3 transition-transform ${synopsisOpen ? '' : '-rotate-90'}`} />
            剧情概述
          </CollapsibleTrigger>
          <CollapsibleContent className="mt-1">
            {isEditing ? (
              <Textarea
                value={draft.synopsis}
                onChange={(e) => updateDraft({ synopsis: e.target.value })}
                rows={4}
                className="text-sm"
              />
            ) : (
              <p className="text-xs text-muted-foreground leading-relaxed">{current.synopsis}</p>
            )}
          </CollapsibleContent>
        </Collapsible>

        <Separator />

        {/* Chapters */}
        {isEditing ? (
          <div className="grid grid-cols-2 gap-2">
            <div>
              <label className="text-[10px] text-muted-foreground">起始章节</label>
              <Input
                value={draft.novel_chapter_start}
                onChange={(e) => updateDraft({ novel_chapter_start: e.target.value })}
                className="h-8 text-sm mt-0.5"
              />
            </div>
            <div>
              <label className="text-[10px] text-muted-foreground">结束章节</label>
              <Input
                value={draft.novel_chapter_end}
                onChange={(e) => updateDraft({ novel_chapter_end: e.target.value })}
                className="h-8 text-sm mt-0.5"
              />
            </div>
          </div>
        ) : (
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <Film className="h-3 w-3" />
            第 {current.novel_chapter_start} - {current.novel_chapter_end} 章
          </div>
        )}

        {/* Duration & Shots */}
        {isEditing ? (
          <div className="grid grid-cols-2 gap-2">
            <div>
              <label className="text-[10px] text-muted-foreground">时长（秒）</label>
              <Input
                type="number"
                value={draft.estimated_duration_sec}
                onChange={(e) => updateDraft({ estimated_duration_sec: parseInt(e.target.value) || 0 })}
                className="h-8 text-sm mt-0.5"
              />
            </div>
            <div>
              <label className="text-[10px] text-muted-foreground">镜头数</label>
              <Input
                type="number"
                min={1}
                max={20}
                value={draft.storyboard_shot_count}
                onChange={(e) => updateDraft({ storyboard_shot_count: parseInt(e.target.value) || 1 })}
                className="h-8 text-sm mt-0.5"
              />
            </div>
          </div>
        ) : (
          <div className="flex items-center gap-4 text-xs text-muted-foreground">
            <span className="flex items-center gap-1">
              <Clock className="h-3 w-3" />
              {current.estimated_duration_sec}秒
            </span>
            <span className="flex items-center gap-1">
              <Film className="h-3 w-3" />
              {current.storyboard_shot_count} 个镜头
            </span>
          </div>
        )}

        <Separator />

        {/* Scores */}
        <div>
          <p className="text-xs font-medium text-foreground mb-2">五维评分（{total}/50）</p>
          <div className="space-y-2">
            {Object.entries(current.scores).map(([key, val]) => (
              <div key={key} className="flex items-center gap-2">
                <span className="text-[11px] text-muted-foreground w-16 shrink-0">
                  {scoreLabels[key]}
                </span>
                {isEditing ? (
                  <Slider
                    min={0}
                    max={10}
                    step={1}
                    value={[draft.scores[key as keyof typeof draft.scores]]}
                    onValueChange={([v]) => updateScore(key, v)}
                    className="flex-1"
                  />
                ) : (
                  <Progress value={val * 10} className="flex-1 h-1.5" />
                )}
                <span className="text-[11px] font-medium w-5 text-right">{val}</span>
              </div>
            ))}
          </div>
        </div>

        <Separator />

        {/* Characters */}
        <div>
          <p className="text-[10px] text-muted-foreground uppercase tracking-wide mb-1 flex items-center gap-1">
            <Users className="h-3 w-3" /> 角色
          </p>
          {isEditing ? (
            <Input
              value={draft.characters.join(', ')}
              onChange={(e) =>
                updateDraft({
                  characters: e.target.value.split(',').map((s) => s.trim()).filter(Boolean),
                })
              }
              placeholder="用逗号分隔"
              className="h-8 text-sm"
            />
          ) : (
            <div className="flex flex-wrap gap-1">
              {current.characters.map((char) => (
                <Badge key={char} variant="outline" className="text-xs">
                  {char}
                </Badge>
              ))}
            </div>
          )}
        </div>

        {/* Style Notes */}
        <Collapsible open={styleOpen} onOpenChange={setStyleOpen}>
          <CollapsibleTrigger className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground w-full">
            <ChevronDown className={`h-3 w-3 transition-transform ${styleOpen ? '' : '-rotate-90'}`} />
            分镜风格指导
          </CollapsibleTrigger>
          <CollapsibleContent className="mt-1">
            {isEditing ? (
              <Textarea
                value={draft.storyboard_style_notes}
                onChange={(e) => updateDraft({ storyboard_style_notes: e.target.value })}
                rows={3}
                className="text-sm"
              />
            ) : (
              <p className="text-xs text-muted-foreground leading-relaxed">
                {current.storyboard_style_notes}
              </p>
            )}
          </CollapsibleContent>
        </Collapsible>
      </CardContent>
    </Card>
  );
}
