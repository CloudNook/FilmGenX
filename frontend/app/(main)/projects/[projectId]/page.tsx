'use client';

import { useEffect, use, useState } from 'react';
import Link from 'next/link';
import { AppLayout } from '@/components/layout';
import { projectsApi, type ProjectResponse } from '@/lib/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Brain, FolderOpen, GitBranch, Loader2 } from 'lucide-react';

const QUICK_LINKS = [
  {
    icon: Brain,
    label: 'AI 工作台',
    description: '与单 Agent 直接交互、独立调试 prompt 与工具',
    suffix: 'workspace',
  },
  {
    icon: GitBranch,
    label: 'AI Supervisor',
    description: '7 步生产链路：outline → script → storyboard → visual_style → character_ref → scene_ref → video_prompt',
    suffix: 'supervisor',
  },
  {
    icon: FolderOpen,
    label: '素材库',
    description: '项目级素材：图片 / 视频 / 音频，按 asset_type 分类',
    suffix: 'materials',
  },
];

export default function ProjectOverviewPage({
  params,
}: {
  params: Promise<{ projectId: string }>;
}) {
  const { projectId } = use(params);
  const projectIdNum = Number(projectId);

  const [project, setProject] = useState<ProjectResponse | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (isNaN(projectIdNum)) return;
    projectsApi
      .get(projectIdNum)
      .then(setProject)
      .catch(() => setProject(null))
      .finally(() => setLoading(false));
  }, [projectIdNum]);

  if (loading) {
    return (
      <AppLayout>
        <div className="flex items-center justify-center h-full">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
        </div>
      </AppLayout>
    );
  }

  if (!project) {
    return (
      <AppLayout>
        <div className="flex items-center justify-center h-full">
          <p className="text-muted-foreground">项目不存在</p>
        </div>
      </AppLayout>
    );
  }

  return (
    <AppLayout>
      <div className="container mx-auto max-w-5xl px-6 py-10 space-y-8">
        <div className="space-y-2">
          <h1 className="text-2xl font-semibold">{project.name}</h1>
          {project.novel_title && (
            <p className="text-sm text-muted-foreground">原著：{project.novel_title}</p>
          )}
          {project.description && (
            <p className="text-sm leading-relaxed text-muted-foreground">{project.description}</p>
          )}
        </div>

        <div className="grid gap-4 md:grid-cols-3">
          {QUICK_LINKS.map(({ icon: Icon, label, description, suffix }) => (
            <Link key={suffix} href={`/projects/${projectId}/${suffix}`}>
              <Card className="h-full transition-colors hover:border-primary/40">
                <CardHeader className="flex flex-row items-center gap-3 pb-2">
                  <Icon className="h-5 w-5 text-primary" />
                  <CardTitle className="text-base">{label}</CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-xs leading-5 text-muted-foreground">{description}</p>
                </CardContent>
              </Card>
            </Link>
          ))}
        </div>
      </div>
    </AppLayout>
  );
}
