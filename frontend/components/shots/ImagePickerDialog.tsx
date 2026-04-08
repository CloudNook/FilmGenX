'use client';

import { useState, useEffect, useCallback, useRef } from 'react';
import {
  charactersApi,
  locationsApi,
  type CharacterResponse,
  type LocationResponse,
} from '@/lib/api';
import type { ImageRef } from '@/lib/api';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Badge } from '@/components/ui/badge';
import { Loader2, ImageIcon, Check, Star, User, MapPin } from 'lucide-react';
import { ScrollArea } from '@/components/ui/scroll-area';

interface ImagePickerDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  projectId: number;
  /** 当前镜头组已有的 image_references */
  existingRefs?: ImageRef[];
  existingImageStartUrl?: string | null;
  onConfirm: (refs: ImageRef[], imageStartUrl: string | null) => void;
}

interface ImageItem {
  url: string;
  label: string;
  /** 来源角色ID */
  characterId?: number;
  /** 来源场景ID */
  locationId?: number;
  /** 角色或场景的显示名称 */
  name?: string;
}

export function ImagePickerDialog({
  open,
  onOpenChange,
  projectId,
  existingRefs = [],
  existingImageStartUrl = null,
  onConfirm,
}: ImagePickerDialogProps) {
  const [selectedRefs, setSelectedRefs] = useState<ImageRef[]>([]);
  const [imageStartUrl, setImageStartUrl] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState<string>('characters');

  const existingRefsRef = useRef(existingRefs);
  useEffect(() => { existingRefsRef.current = existingRefs; }, [existingRefs]);

  // All available images from API
  const [characterImages, setCharacterImages] = useState<
    { character: { id: number; name: string }; images: ImageItem[] }[]
  >([]);
  const [locationImages, setLocationImages] = useState<
    { location: { id: number; name: string }; images: ImageItem[] }[]
  >([]);

  // Build URL → ImageRef map
  const urlToRef = useCallback((url: string, item: ImageItem): ImageRef => ({
    url,
    label: `${item.characterId ? '角色' : '场景'} - ${item.label}`,
    name: item.name,
    ...(item.characterId ? { character_id: item.characterId } : {}),
    ...(item.locationId ? { location_id: item.locationId } : {}),
  }), []);

  // Reset selection when dialog opens
  useEffect(() => {
    if (open) {
      setSelectedRefs([...existingRefs]);
      setImageStartUrl(existingImageStartUrl ?? null);
    }
  }, [open, existingRefs, existingImageStartUrl]);

  // Fetch images when dialog opens
  useEffect(() => {
    if (!open || !projectId) return;
    setLoading(true);
    Promise.all([
      fetchCharacterImages(projectId),
      fetchLocationImages(projectId),
    ])
      .then(([chars, locs]) => {
        setCharacterImages(chars);
        setLocationImages(locs);
      })
      .finally(() => setLoading(false));
  }, [open, projectId]);

  const isUrlSelected = useCallback(
    (url: string) => selectedRefs.some((r) => r.url === url),
    [selectedRefs],
  );

  const toggleRef = useCallback(
    (item: ImageItem) => {
      const ref = urlToRef(item.url, item);
      setSelectedRefs((prev) => {
        const exists = prev.some((r) => r.url === item.url);
        if (exists) {
          const next = prev.filter((r) => r.url !== item.url);
          setImageStartUrl((cur) => (cur === item.url ? null : cur));
          return next;
        }
        return [...prev, ref];
      });
    },
    [urlToRef],
  );

  const setAsStart = useCallback(
    (item: ImageItem) => {
      const ref = urlToRef(item.url, item);
      setImageStartUrl((prev) => (prev === item.url ? null : item.url));
      setSelectedRefs((prev) => {
        if (prev.some((r) => r.url === item.url)) return prev;
        return [...prev, ref];
      });
    },
    [urlToRef],
  );

  const handleConfirm = useCallback(() => {
    onConfirm(selectedRefs, imageStartUrl);
  }, [selectedRefs, imageStartUrl, onConfirm]);

  const selectedCount = selectedRefs.length;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-3xl max-h-[80vh] flex flex-col">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <ImageIcon className="h-5 w-5" />
            选择参考图
            {selectedCount > 0 && (
              <Badge variant="secondary" className="ml-2">
                已选 {selectedCount} 张
              </Badge>
            )}
          </DialogTitle>
        </DialogHeader>

        {loading ? (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
            <span className="ml-2 text-sm text-muted-foreground">加载中...</span>
          </div>
        ) : (
          <Tabs value={activeTab} onValueChange={setActiveTab} className="flex-1 min-h-0 flex flex-col">
            <TabsList className="grid w-full grid-cols-2">
              <TabsTrigger value="characters" className="flex items-center gap-1.5">
                <User className="h-3.5 w-3.5" />
                角色图
                {characterImages.reduce((acc, c) => acc + c.images.length, 0) > 0 && (
                  <Badge variant="outline" className="ml-1 text-[10px] h-4 px-1">
                    {characterImages.reduce((acc, c) => acc + c.images.length, 0)}
                  </Badge>
                )}
              </TabsTrigger>
              <TabsTrigger value="locations" className="flex items-center gap-1.5">
                <MapPin className="h-3.5 w-3.5" />
                场景图
                {locationImages.reduce((acc, l) => acc + l.images.length, 0) > 0 && (
                  <Badge variant="outline" className="ml-1 text-[10px] h-4 px-1">
                    {locationImages.reduce((acc, l) => acc + l.images.length, 0)}
                  </Badge>
                )}
              </TabsTrigger>
            </TabsList>

            <ScrollArea className="flex-1 min-h-0 mt-4">
              <TabsContent value="characters" className="mt-0">
                {characterImages.length === 0 ? (
                  <p className="text-sm text-muted-foreground text-center py-8">
                    暂无角色图片，请先在素材库中上传角色图
                  </p>
                ) : (
                  <div className="space-y-4">
                    {characterImages.map((item) =>
                      item.images.length > 0 ? (
                        <div key={`char-${item.character.id}`}>
                          <div className="flex items-center gap-2 mb-2">
                            <span className="text-sm font-medium text-foreground">
                              {item.character.name}
                            </span>
                          </div>
                          <div className="grid grid-cols-4 gap-2">
                            {item.images.map((img) => (
                              <ImageCard
                                key={img.url}
                                url={img.url}
                                label={img.label}
                                selected={isUrlSelected(img.url)}
                                isStart={imageStartUrl === img.url}
                                onToggle={() => toggleRef(img)}
                                onSetStart={() => setAsStart(img)}
                              />
                            ))}
                          </div>
                        </div>
                      ) : null
                    )}
                  </div>
                )}
              </TabsContent>

              <TabsContent value="locations" className="mt-0">
                {locationImages.length === 0 ? (
                  <p className="text-sm text-muted-foreground text-center py-8">
                    暂无场景图片，请先在素材库中上传场景图
                  </p>
                ) : (
                  <div className="space-y-4">
                    {locationImages.map((item) =>
                      item.images.length > 0 ? (
                        <div key={`loc-${item.location.id}`}>
                          <div className="flex items-center gap-2 mb-2">
                            <span className="text-sm font-medium text-foreground">
                              {item.location.name}
                            </span>
                          </div>
                          <div className="grid grid-cols-4 gap-2">
                            {item.images.map((img) => (
                              <ImageCard
                                key={img.url}
                                url={img.url}
                                label={img.label}
                                selected={isUrlSelected(img.url)}
                                isStart={imageStartUrl === img.url}
                                onToggle={() => toggleRef(img)}
                                onSetStart={() => setAsStart(img)}
                              />
                            ))}
                          </div>
                        </div>
                      ) : null
                    )}
                  </div>
                )}
              </TabsContent>
            </ScrollArea>
          </Tabs>
        )}

        <DialogFooter className="flex-shrink-0">
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            取消
          </Button>
          <Button onClick={handleConfirm}>
            <Check className="h-4 w-4 mr-1" />
            {selectedCount === 0 ? '清除选择' : `确认选择 (${selectedCount} 张)`}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

// ---------------------------------------------------------------------------
// Image Card sub-component
// ---------------------------------------------------------------------------

function ImageCard({
  url,
  label,
  selected,
  isStart,
  onToggle,
  onSetStart,
}: {
  url: string;
  label: string;
  selected: boolean;
  isStart: boolean;
  onToggle: () => void;
  onSetStart: () => void;
}) {
  return (
    <div
      className={`relative rounded-lg border overflow-hidden cursor-pointer transition-all ${
        selected
          ? 'border-primary ring-2 ring-primary/30'
          : 'border-border hover:border-primary/50'
      }`}
      onClick={onToggle}
    >
      <div className="aspect-square bg-muted/60">
        <img src={url} alt={label} className="w-full h-full object-cover" loading="lazy" />
      </div>
      {selected && (
        <div className="absolute top-1 right-1 bg-primary rounded-full w-5 h-5 flex items-center justify-center">
          <Check className="h-3 w-3 text-primary-foreground" />
        </div>
      )}
      {isStart && (
        <div className="absolute top-1 left-1 bg-amber-500 rounded-full w-5 h-5 flex items-center justify-center">
          <Star className="h-3 w-3 text-white" />
        </div>
      )}
      <div className="px-1.5 py-1 bg-secondary/80">
        <p className="text-[10px] text-muted-foreground truncate">{label}</p>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Data fetching helpers
// ---------------------------------------------------------------------------

async function fetchCharacterImages(
  projectId: number,
): Promise<{ character: { id: number; name: string }; images: ImageItem[] }[]> {
  try {
    const page = await charactersApi.list(projectId, 1, 100);
    const result: { character: { id: number; name: string }; images: ImageItem[] }[] = [];
    for (const char of page.items) {
      const images: ImageItem[] = [];
      if (char.pic_url) {
        images.push({
          url: char.pic_url,
          label: '角色图',
          characterId: char.id,
          name: char.name,
        });
      }
      if (images.length > 0) {
        result.push({ character: { id: char.id, name: char.name }, images });
      }
    }
    return result;
  } catch {
    return [];
  }
}

async function fetchLocationImages(
  projectId: number,
): Promise<{ location: { id: number; name: string }; images: ImageItem[] }[]> {
  try {
    const page = await locationsApi.list(projectId, 1, 100);
    const details = await Promise.all(
      page.items.map((l) => locationsApi.get(projectId, l.id)),
    );
    const result: { location: { id: number; name: string }; images: ImageItem[] }[] = [];
    for (const detail of details) {
      const images: ImageItem[] = [];
      if (detail.pic_url) {
        images.push({
          url: detail.pic_url,
          label: '场景封面图',
          locationId: detail.id,
          name: detail.name,
        });
      }
      if (images.length > 0) {
        result.push({ location: { id: detail.id, name: detail.name }, images });
      }
    }
    return result;
  } catch {
    return [];
  }
}
