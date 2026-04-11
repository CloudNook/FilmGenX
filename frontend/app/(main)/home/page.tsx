'use client';

import { AppLayout } from '@/components/layout';
import { useAuth } from '@/lib/auth';

export default function HomePage() {
  const { user } = useAuth();

  const getGreeting = () => {
    const hour = new Date().getHours();
    if (hour < 6) return '夜深了';
    if (hour < 12) return '早上好';
    if (hour < 14) return '中午好';
    if (hour < 18) return '下午好';
    return '晚上好';
  };

  return (
    <AppLayout>
      <div className="flex items-center justify-center h-full p-6">
        <div className="text-center space-y-4">
          <h1 className="text-4xl font-bold text-foreground">
            {getGreeting()}，{user?.username || '用户'}
          </h1>
          <p className="text-lg text-muted-foreground">
            欢迎使用 FilmGenX，开始你的创作之旅
          </p>
        </div>
      </div>
    </AppLayout>
  );
}
