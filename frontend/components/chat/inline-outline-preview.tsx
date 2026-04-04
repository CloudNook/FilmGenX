'use client';

import type { EpisodeOutline } from '@/lib/api';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { FileText, ChevronRight } from 'lucide-react';

interface InlineOutlinePreviewProps {
  outline: EpisodeOutline;
  onClick?: () => void;
}

const scoreLabels: Record<string, string> = {
  dramatic_tension: '戏剧张力',
  visual_potential: '视觉潜力',
  emotional_resonance: '情感共鸣',
  narrative_importance: '叙事重要性',
  audience_familiarity: '观众熟知度',
};

export function InlineOutlinePreview({ outline, onClick }: InlineOutlinePreviewProps) {
  const scores = outline.scores;
  const total =
    scores.dramatic_tension +
    scores.visual_potential +
    scores.emotional_resonance +
    scores.narrative_importance +
    scores.audience_familiarity;

  return (
    <button
      onClick={onClick}
      className="w-full text-left rounded-xl border border-warning/30 bg-warning/5 p-4 hover:bg-warning/10 transition-colors"
    >
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-2">
          <div className="h-8 w-8 rounded-lg bg-warning/20 flex items-center justify-center">
            <FileText className="h-4 w-4 text-warning" />
          </div>
          <div>
            <p className="font-medium text-foreground text-sm">{outline.title}</p>
            <p className="text-xs text-muted-foreground">
              {outline.episode_code} · v{outline.version}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-1 text-muted-foreground">
          <span className="text-xs">在侧栏查看</span>
          <ChevronRight className="h-3 w-3" />
        </div>
      </div>

      <p className="text-xs text-muted-foreground line-clamp-2 mb-3">{outline.synopsis}</p>

      {/* Mini scores */}
      <div className="flex items-center gap-3 mb-2">
        {Object.entries(scores).map(([key, val]) => (
          <div key={key} className="flex items-center gap-1">
            <span className="text-[10px] text-muted-foreground">{scoreLabels[key]?.slice(0, 2)}</span>
            <Progress value={val * 10} className="h-1 w-8" />
          </div>
        ))}
        <span className="text-xs font-medium text-foreground ml-auto">{total}/50</span>
      </div>

      {/* Characters */}
      <div className="flex flex-wrap gap-1">
        {outline.characters.slice(0, 4).map((char) => (
          <Badge key={char} variant="outline" className="text-[10px] h-5">
            {char}
          </Badge>
        ))}
        {outline.characters.length > 4 && (
          <Badge variant="outline" className="text-[10px] h-5">
            +{outline.characters.length - 4}
          </Badge>
        )}
      </div>
    </button>
  );
}
