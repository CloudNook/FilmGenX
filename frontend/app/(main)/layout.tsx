/**
 * 需要鉴权的页面 layout。
 * 包裹 projects 等所有需要登录的页面。
 */
'use client';

import { RequireAuth } from '@/components/require-auth';

export default function MainLayout({ children }: { children: React.ReactNode }) {
  return <RequireAuth>{children}</RequireAuth>;
}
