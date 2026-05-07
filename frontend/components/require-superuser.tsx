'use client';

import { useEffect, useRef } from 'react';
import { useRouter } from 'next/navigation';
import { toast } from 'sonner';
import { useAuth } from '@/lib/auth';

/**
 * Superuser 路由守卫。
 *
 * 包裹仅 ``is_superuser`` 可访问的页面：
 * - 未登录 → ``/login``（也可以在外层先包 RequireAuth；这里兜底）
 * - 已登录但非 superuser → 提示并跳转 ``/home``
 * - 加载中 → 全屏 loading
 */
export function RequireSuperuser({ children }: { children: React.ReactNode }) {
  const { isLoading, isAuthenticated, user } = useAuth();
  const router = useRouter();
  const notifiedRef = useRef(false);

  useEffect(() => {
    if (isLoading) return;
    if (!isAuthenticated) {
      router.replace('/login');
      return;
    }
    if (user && !user.is_superuser) {
      // 防止 effect 重复触发时反复 toast
      if (!notifiedRef.current) {
        notifiedRef.current = true;
        toast.error('需要管理员权限才能访问该页面');
      }
      router.replace('/home');
    }
  }, [isLoading, isAuthenticated, user, router]);

  if (isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background">
        <div className="flex flex-col items-center gap-4">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
          <p className="text-sm text-muted-foreground">加载中...</p>
        </div>
      </div>
    );
  }

  if (!isAuthenticated || !user || !user.is_superuser) {
    return null;
  }

  return <>{children}</>;
}
