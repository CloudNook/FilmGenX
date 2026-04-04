'use client';

import type { EpisodeOutline } from '@/lib/api';
import { Badge } from '@/components/ui/badge';
import { FileText, ChevronRight, MapPin, Music, Film } from 'lucide-react';

interface InlineOutlinePreviewProps {
  outline: EpisodeOutline;
  onClick?: () => void;
}

export function InlineOutlinePreview({ outline, onClick }: InlineOutlinePreviewProps) {
  return (
    <button
      onClick={onClick}
      className="w-full text-left rounded-xl border border-warning/30 bg-warning/5 p-4 hover:bg-warning/10 transition-colors"
    >
      {/* Header */}
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-2">
          <div className="h-8 w-8 rounded-lg bg-warning/20 flex items-center justify-center">
            <FileText className="h-4 w-4 text-warning" />
          </div>
          <div>
            <p className="font-medium text-foreground text-sm">{outline.title}</p>
            <p className="text-xs text-muted-foreground">
              {outline.episode_code ? `${outline.episode_code} · ` : ''}v{outline.version}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-1 text-muted-foreground">
          <span className="text-xs">在侧栏查看</span>
          <ChevronRight className="h-3 w-3" />
        </div>
      </div>

      {/* Theme */}
      {outline.theme && (
        <p className="text-xs text-warning font-medium mb-1">{outline.theme}</p>
      )}

      {/* Synopsis */}
      <p className="text-xs text-muted-foreground line-clamp-2 mb-3">{outline.synopsis}</p>

      {/* Key info row */}
      <div className="flex items-center gap-3 mb-2 text-[10px] text-muted-foreground">
        {outline.primary_location && (
          <span className="flex items-center gap-1">
            <MapPin className="h-3 w-3" />
            {outline.primary_location}
          </span>
        )}
        {outline.bgm_direction && (
          <span className="flex items-center gap-1">
            <Music className="h-3 w-3" />
            {outline.bgm_direction.slice(0, 12)}…
          </span>
        )}
        <span className="flex items-center gap-1 ml-auto">
          <Film className="h-3 w-3" />
          {outline.storyboard_shot_count} 镜头
        </span>
      </div>

      {/* Story arc */}
      {outline.story_arc && (
        <p className="text-[10px] text-muted-foreground mb-2 italic">{outline.story_arc}</p>
      )}

      {/* Characters */}
      <div className="flex flex-wrap gap-1">
        {(outline.characters || []).slice(0, 4).map((char) => (
          <Badge key={char} variant="outline" className="text-[10px] h-5">
            {char}
          </Badge>
        ))}
        {(outline.characters || []).length > 4 && (
          <Badge variant="outline" className="text-[10px] h-5">
            +{outline.characters.length - 4}
          </Badge>
        )}
      </div>
    </button>
  );
}
