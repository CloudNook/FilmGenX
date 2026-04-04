'use client';

import { Sidebar } from './sidebar';
import { Header } from './header';

interface AppLayoutProps {
  children: React.ReactNode;
  projectId?: string;
  title?: string;
  showSearch?: boolean;
  breadcrumbs?: Array<{ label: string; href?: string }>;
}

export function AppLayout({
  children,
  projectId,
  title,
  showSearch = true,
  breadcrumbs,
}: AppLayoutProps) {
  return (
    <div className="flex h-screen overflow-hidden bg-background">
      <Sidebar projectId={projectId} />
      <div className="flex flex-1 flex-col overflow-hidden">
        <Header title={title} showSearch={showSearch} breadcrumbs={breadcrumbs} />
        <main className="flex-1 overflow-y-auto">{children}</main>
      </div>
    </div>
  );
}
