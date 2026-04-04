'use client';

import { useState } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { cn } from '@/lib/utils';
import {
  Film,
  FolderOpen,
  MessageSquare,
  Clapperboard,
  Video,
  Users,
  Settings,
  ChevronLeft,
  ChevronRight,
  Home,
  Sparkles,
  Box,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';

interface SidebarProps {
  projectId?: string;
}

interface NavItem {
  title: string;
  href: string;
  icon: React.ComponentType<{ className?: string }>;
  badge?: number;
}

export function Sidebar({ projectId }: SidebarProps) {
  const [collapsed, setCollapsed] = useState(false);
  const pathname = usePathname();

  const mainNavItems: NavItem[] = [
    { title: '首页', href: '/', icon: Home },
    { title: '项目列表', href: '/projects', icon: FolderOpen },
  ];

  const projectNavItems: NavItem[] = projectId
    ? [
        { title: '项目概览', href: `/projects/${projectId}`, icon: Film },
        { title: '素材库', href: `/projects/${projectId}/materials`, icon: Box },
        { title: 'AI 剧本', href: `/projects/${projectId}/chat`, icon: MessageSquare},
        { title: '分集管理', href: `/projects/${projectId}/episodes`, icon: Clapperboard },
        { title: '分镜工作台', href: `/projects/${projectId}/storyboard`, icon: Sparkles },
        { title: '视频制作', href: `/projects/${projectId}/video`, icon: Video },
      ]
    : [];

  const bottomNavItems: NavItem[] = [
    { title: '全局设置', href: '/settings', icon: Settings },
  ];

  const renderNavItem = (item: NavItem) => {
    const isActive = pathname === item.href || (item.href !== '/' && pathname.startsWith(item.href));
    const Icon = item.icon;

    const content = (
      <Link
        href={item.href}
        className={cn(
          'flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-all',
          'hover:bg-secondary/80',
          isActive
            ? 'bg-primary/10 text-primary'
            : 'text-muted-foreground hover:text-foreground'
        )}
      >
        <Icon className={cn('h-5 w-5 shrink-0', isActive && 'text-primary')} />
        {!collapsed && (
          <>
            <span className="flex-1 truncate">{item.title}</span>
            {item.badge && (
              <span className="flex h-5 min-w-5 items-center justify-center rounded-full bg-primary px-1.5 text-xs font-semibold text-primary-foreground">
                {item.badge}
              </span>
            )}
          </>
        )}
      </Link>
    );

    if (collapsed) {
      return (
        <TooltipProvider key={item.href} delayDuration={0}>
          <Tooltip>
            <TooltipTrigger asChild>{content}</TooltipTrigger>
            <TooltipContent side="right" className="flex items-center gap-2">
              {item.title}
              {item.badge && (
                <span className="flex h-5 min-w-5 items-center justify-center rounded-full bg-primary px-1.5 text-xs font-semibold text-primary-foreground">
                  {item.badge}
                </span>
              )}
            </TooltipContent>
          </Tooltip>
        </TooltipProvider>
      );
    }

    return <div key={item.href}>{content}</div>;
  };

  return (
    <aside
      className={cn(
        'flex h-screen flex-col border-r border-sidebar-border bg-sidebar transition-all duration-300',
        collapsed ? 'w-16' : 'w-64'
      )}
    >
      {/* Logo */}
      <div className="flex h-16 items-center justify-between border-b border-sidebar-border px-4">
        {!collapsed && (
          <Link href="/" className="flex items-center gap-2">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary">
              <Film className="h-5 w-5 text-primary-foreground" />
            </div>
            <span className="text-lg font-bold text-foreground">FilmGenX</span>
          </Link>
        )}
        {collapsed && (
          <div className="mx-auto flex h-8 w-8 items-center justify-center rounded-lg bg-primary">
            <Film className="h-5 w-5 text-primary-foreground" />
          </div>
        )}
      </div>

      {/* Navigation */}
      <nav className="flex-1 space-y-1 overflow-y-auto p-3">
        {/* Main Nav */}
        <div className="space-y-1">
          {mainNavItems.map(renderNavItem)}
        </div>

        {/* Project Nav */}
        {projectNavItems.length > 0 && (
          <>
            <div className="my-4 border-t border-sidebar-border" />
            {!collapsed && (
              <p className="mb-2 px-3 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                当前项目
              </p>
            )}
            <div className="space-y-1">
              {projectNavItems.map(renderNavItem)}
            </div>
          </>
        )}
      </nav>

      {/* Bottom Nav */}
      <div className="border-t border-sidebar-border p-3">
        <div className="space-y-1">
          {bottomNavItems.map(renderNavItem)}
        </div>

        {/* Collapse Button */}
        <Button
          variant="ghost"
          size="sm"
          className="mt-2 w-full justify-center text-muted-foreground hover:text-foreground"
          onClick={() => setCollapsed(!collapsed)}
        >
          {collapsed ? (
            <ChevronRight className="h-4 w-4" />
          ) : (
            <>
              <ChevronLeft className="h-4 w-4 mr-2" />
              <span>收起侧边栏</span>
            </>
          )}
        </Button>
      </div>
    </aside>
  );
}
