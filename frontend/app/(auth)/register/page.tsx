'use client';

import Link from 'next/link';
import { Film, Lock } from 'lucide-react';

export default function RegisterPage() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-background">
      <div className="w-full max-w-sm space-y-6 text-center px-6">
        <Link href="/" className="inline-flex items-center gap-3 justify-center">
          <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-primary">
            <Film className="h-7 w-7 text-primary-foreground" />
          </div>
          <span className="text-2xl font-bold text-foreground">FilmGenX</span>
        </Link>

        <div className="rounded-xl border border-border bg-card p-8 space-y-4">
          <div className="flex justify-center">
            <div className="flex h-12 w-12 items-center justify-center rounded-full bg-muted">
              <Lock className="h-6 w-6 text-muted-foreground" />
            </div>
          </div>
          <h2 className="text-xl font-semibold text-foreground">注册暂不开放</h2>
          <p className="text-sm text-muted-foreground">
            当前仅限受邀用户使用，如需访问请联系管理员获取邀请码。
          </p>
          <Link
            href="/login"
            className="block w-full rounded-lg bg-primary px-4 py-2.5 text-sm font-medium text-primary-foreground hover:bg-primary/90 transition-colors"
          >
            返回登录
          </Link>
        </div>
      </div>
    </div>
  );
}
