'use client';

import { useState, useEffect } from 'react';
import type { EpisodeOutline, KeyEvent, VisualHighlight } from '@/lib/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Separator } from '@/components/ui/separator';
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
import {
  Edit, Check, X, ChevronDown, Star, Clock, Film, Users,
  MapPin, Music, Sparkles, ArrowRight,
} from 'lucide-react';

interface OutlineCardProps {
  outline: EpisodeOutline;
  isEditing: boolean;
  onEditStart: () => void;
  onSave: (outline: EpisodeOutline) => void;
  onCancel: () => void;
  readOnly?: boolean;
}

const priorityOptions = [
  { value: 'S', label: 'S 级（旗舰）' },
  { value: 'A', label: 'A 级（高质量）' },
  { value: 'B', label: 'B 级（常规）' },
  { value: 'C', label: 'C 级（补充）' },
];

export function OutlineCard({
  outline,
  isEditing,
  onEditStart,
  onSave,
  onCancel,
  readOnly = false,
}: OutlineCardProps) {
  const [draft, setDraft] = useState<EpisodeOutline>({ ...outline });
  const [synopsisOpen, setSynopsisOpen] = useState(true);
  const [eventsOpen, setEventsOpen] = useState(true);
  const [visualOpen, setVisualOpen] = useState(false);
  const [styleOpen, setStyleOpen] = useState(false);

  useEffect(() => {
    if (!isEditing) setDraft({ ...outline });
  }, [outline, isEditing]);

  const current = isEditing ? draft : outline;
  const update = (patch: Partial<EpisodeOutline>) => setDraft((p) => ({ ...p, ...patch }));

  return (
    <Card className="border-border">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm font-medium flex items-center gap-2">
            <Star className="h-4 w-4 text-warning" />
            {readOnly ? '已确认大纲' : `大纲草稿 v${current.version}`}
          </CardTitle>
          {!isEditing && !readOnly ? (
            <Button variant="ghost" size="sm" className="h-7 text-xs" onClick={onEditStart}>
              <Edit className="h-3 w-3 mr-1" />编辑
            </Button>
          ) : isEditing ? (
            <div className="flex gap-1">
              <Button variant="ghost" size="sm" className="h-7 text-xs text-destructive"
                onClick={() => { setDraft({ ...outline }); onCancel(); }}>
                <X className="h-3 w-3 mr-1" />取消
              </Button>
              <Button size="sm" className="h-7 text-xs" onClick={() => onSave(draft)}>
                <Check className="h-3 w-3 mr-1" />保存
              </Button>
            </div>
          ) : null}
        </div>
      </CardHeader>

      <CardContent className="space-y-3">
        {/* Title & Code */}
        {isEditing ? (
          <div className="grid grid-cols-2 gap-2">
            <div>
              <label className="text-[10px] text-muted-foreground uppercase tracking-wide">标题</label>
              <Input value={draft.title} onChange={(e) => update({ title: e.target.value })} className="h-8 text-sm mt-0.5" />
            </div>
            <div>
              <label className="text-[10px] text-muted-foreground uppercase tracking-wide">编号</label>
              <Input value={draft.episode_code || ''} onChange={(e) => update({ episode_code: e.target.value })} className="h-8 text-sm mt-0.5" />
            </div>
          </div>
        ) : (
          <div>
            <p className="font-medium text-foreground">{current.title}</p>
            {current.episode_code && <p className="text-xs text-muted-foreground">{current.episode_code}</p>}
            {current.theme && <p className="text-xs text-warning mt-0.5">{current.theme}</p>}
          </div>
        )}

        {/* Priority & Duration & Shots */}
        {isEditing ? (
          <div className="grid grid-cols-3 gap-2">
            <div>
              <label className="text-[10px] text-muted-foreground">优先级</label>
              <Select value={draft.priority} onValueChange={(v) => update({ priority: v })}>
                <SelectTrigger className="h-8 text-sm mt-0.5"><SelectValue /></SelectTrigger>
                <SelectContent>
                  {priorityOptions.map((o) => <SelectItem key={o.value} value={o.value}>{o.label}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
            <div>
              <label className="text-[10px] text-muted-foreground">时长（秒）</label>
              <Input type="number" value={draft.estimated_duration_sec}
                onChange={(e) => update({ estimated_duration_sec: parseInt(e.target.value) || 0 })}
                className="h-8 text-sm mt-0.5" />
            </div>
            <div>
              <label className="text-[10px] text-muted-foreground">镜头数</label>
              <Input type="number" min={1} max={20} value={draft.storyboard_shot_count}
                onChange={(e) => update({ storyboard_shot_count: parseInt(e.target.value) || 1 })}
                className="h-8 text-sm mt-0.5" />
            </div>
          </div>
        ) : (
          <div className="flex items-center gap-3 text-xs text-muted-foreground">
            <Badge variant="outline">{current.priority} 级</Badge>
            <span className="flex items-center gap-1"><Clock className="h-3 w-3" />{current.estimated_duration_sec}秒</span>
            <span className="flex items-center gap-1"><Film className="h-3 w-3" />{current.storyboard_shot_count} 镜头</span>
          </div>
        )}

        <Separator />

        {/* Synopsis */}
        <Collapsible open={synopsisOpen} onOpenChange={setSynopsisOpen}>
          <CollapsibleTrigger className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground w-full">
            <ChevronDown className={`h-3 w-3 transition-transform ${synopsisOpen ? '' : '-rotate-90'}`} />
            剧情概述
          </CollapsibleTrigger>
          <CollapsibleContent className="mt-1">
            {isEditing ? (
              <Textarea value={draft.synopsis} onChange={(e) => update({ synopsis: e.target.value })} rows={4} className="text-sm" />
            ) : (
              <p className="text-xs text-muted-foreground leading-relaxed">{current.synopsis}</p>
            )}
          </CollapsibleContent>
        </Collapsible>

        {/* Story Arc */}
        {(current.story_arc || isEditing) && (
          <div>
            <p className="text-[10px] text-muted-foreground uppercase tracking-wide mb-1 flex items-center gap-1">
              <ArrowRight className="h-3 w-3" /> 叙事弧
            </p>
            {isEditing ? (
              <Input value={draft.story_arc || ''} onChange={(e) => update({ story_arc: e.target.value })} className="h-8 text-sm" placeholder="开头→冲突→结尾" />
            ) : (
              <p className="text-xs text-muted-foreground italic">{current.story_arc}</p>
            )}
          </div>
        )}

        {/* Emotional Arc */}
        {(current.emotional_arc || isEditing) && (
          <div>
            <p className="text-[10px] text-muted-foreground uppercase tracking-wide mb-1">情绪走势</p>
            {isEditing ? (
              <Input value={draft.emotional_arc || ''} onChange={(e) => update({ emotional_arc: e.target.value })} className="h-8 text-sm" placeholder="压抑→愤怒→爆发→震撼" />
            ) : (
              <p className="text-xs text-muted-foreground">{current.emotional_arc}</p>
            )}
          </div>
        )}

        <Separator />

        {/* Key Events */}
        {((current.key_events && current.key_events.length > 0) || isEditing) && (
          <Collapsible open={eventsOpen} onOpenChange={setEventsOpen}>
            <CollapsibleTrigger className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground w-full">
              <ChevronDown className={`h-3 w-3 transition-transform ${eventsOpen ? '' : '-rotate-90'}`} />
              关键事件节点
            </CollapsibleTrigger>
            <CollapsibleContent className="mt-1 space-y-1">
              {(current.key_events || []).map((e: KeyEvent) => (
                <div key={e.order} className="flex gap-2 text-xs">
                  <span className="text-muted-foreground shrink-0">{e.order}.</span>
                  <div>
                    <span className="text-foreground">{e.description}</span>
                    <Badge variant="outline" className="ml-1 text-[9px] h-4">{e.emotional_beat}</Badge>
                  </div>
                </div>
              ))}
            </CollapsibleContent>
          </Collapsible>
        )}

        <Separator />

        {/* Chapters */}
        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          <Film className="h-3 w-3" />
          {current.novel_chapter_start} — {current.novel_chapter_end}
        </div>

        {/* Location */}
        {current.primary_location && (
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <MapPin className="h-3 w-3" />
            <span>{current.primary_location}</span>
            {current.location_atmosphere && <span className="text-[10px] italic">· {current.location_atmosphere.slice(0, 20)}…</span>}
          </div>
        )}

        {/* BGM */}
        {current.bgm_direction && (
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <Music className="h-3 w-3" />
            {current.bgm_direction}
          </div>
        )}

        <Separator />

        {/* Characters */}
        <div>
          <p className="text-[10px] text-muted-foreground uppercase tracking-wide mb-1 flex items-center gap-1">
            <Users className="h-3 w-3" /> 角色
          </p>
          {isEditing ? (
            <Input value={(draft.characters || []).join(', ')}
              onChange={(e) => update({ characters: e.target.value.split(',').map((s) => s.trim()).filter(Boolean) })}
              placeholder="用逗号分隔" className="h-8 text-sm" />
          ) : (
            <div className="flex flex-wrap gap-1">
              {(current.characters || []).map((char) => (
                <Badge key={char} variant="outline" className="text-xs">{char}</Badge>
              ))}
            </div>
          )}
          {current.character_focus && !isEditing && (
            <p className="text-[10px] text-muted-foreground mt-1 italic">{current.character_focus}</p>
          )}
        </div>

        {/* Visual Highlights */}
        {((current.visual_highlights && current.visual_highlights.length > 0) || isEditing) && (
          <Collapsible open={visualOpen} onOpenChange={setVisualOpen}>
            <CollapsibleTrigger className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground w-full">
              <ChevronDown className={`h-3 w-3 transition-transform ${visualOpen ? '' : '-rotate-90'}`} />
              视觉亮点
            </CollapsibleTrigger>
            <CollapsibleContent className="mt-1 space-y-1">
              {(current.visual_highlights || []).map((v: VisualHighlight) => (
                <div key={v.name} className="text-xs">
                  <span className="font-medium text-foreground">{v.name}</span>
                  <span className="text-muted-foreground">：{v.description}</span>
                </div>
              ))}
            </CollapsibleContent>
          </Collapsible>
        )}

        {/* Style Notes */}
        <Collapsible open={styleOpen} onOpenChange={setStyleOpen}>
          <CollapsibleTrigger className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground w-full">
            <ChevronDown className={`h-3 w-3 transition-transform ${styleOpen ? '' : '-rotate-90'}`} />
            <Sparkles className="h-3 w-3" /> 分镜风格指导
          </CollapsibleTrigger>
          <CollapsibleContent className="mt-1">
            {isEditing ? (
              <Textarea value={draft.storyboard_style_notes}
                onChange={(e) => update({ storyboard_style_notes: e.target.value })}
                rows={3} className="text-sm" />
            ) : (
              <p className="text-xs text-muted-foreground leading-relaxed">{current.storyboard_style_notes}</p>
            )}
          </CollapsibleContent>
        </Collapsible>

        {/* Episode hooks */}
        {(current.previous_episode_hint || current.next_episode_hint) && (
          <>
            <Separator />
            <div className="space-y-1">
              {current.previous_episode_hint && (
                <p className="text-[10px] text-muted-foreground">
                  <span className="font-medium">上集结尾：</span>{current.previous_episode_hint}
                </p>
              )}
              {current.next_episode_hint && (
                <p className="text-[10px] text-muted-foreground">
                  <span className="font-medium">本集钩子：</span>{current.next_episode_hint}
                </p>
              )}
            </div>
          </>
        )}
      </CardContent>
    </Card>
  );
}
