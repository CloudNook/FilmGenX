/**
 * /admin/* 路由 layout：仅 superuser 可访问。
 *
 * 上层 (main)/layout.tsx 已经做了登录校验；本 layout 只额外加 superuser 检查。
 * 非 admin 用户进入会被弹提示 + 跳转回 /home。
 */
'use client';

import { RequireSuperuser } from '@/components/require-superuser';

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  return <RequireSuperuser>{children}</RequireSuperuser>;
}
