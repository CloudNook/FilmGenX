'use client';

import { useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { Film, Eye, EyeOff, Mail, Lock, ArrowRight } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Checkbox } from '@/components/ui/checkbox';
import { useAuth } from '@/lib/auth';

export default function LoginPage() {
  const router = useRouter();
  const { login } = useAuth();
  const [showPassword, setShowPassword] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [rememberMe, setRememberMe] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setIsLoading(true);

    try {
      await login(email, password);
      router.push('/projects');
    } catch (err: any) {
      setError(err.message || '登录失败，请重试');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen">
      {/* Left Panel - Branding */}
      <div className="hidden lg:flex lg:w-1/2 flex-col justify-between bg-secondary p-12">
        <div>
          <Link href="/" className="flex items-center gap-3">
            <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-primary">
              <Film className="h-7 w-7 text-primary-foreground" />
            </div>
            <span className="text-2xl font-bold text-foreground">FilmGenX</span>
          </Link>
        </div>

        <div className="space-y-6">
          <h1 className="text-4xl font-bold leading-tight text-foreground text-balance">
            新一代 AI 驱动的
            <br />
            <span className="text-primary">动画内容生产系统</span>
          </h1>
          <p className="text-lg text-muted-foreground max-w-md leading-relaxed">
            从剧本到成片的全流程智能化解决方案，让创意无限延伸，让制作更加高效。
          </p>

          {/* Feature List */}
          <div className="space-y-4 pt-4">
            {[
              'AI 智能剧本创作与优化',
              '自动化分镜生成与调整',
              '角色一致性智能管理',
              '多模态内容协同制作',
            ].map((feature, index) => (
              <div key={index} className="flex items-center gap-3">
                <div className="flex h-6 w-6 items-center justify-center rounded-full bg-primary">
                  <div className="h-2 w-2 rounded-full bg-primary-foreground" />
                </div>
                <span className="text-foreground">{feature}</span>
              </div>
            ))}
          </div>
        </div>

        <p className="text-sm text-muted-foreground">
          FilmGenX 2024. 保留所有权利。
        </p>
      </div>

      {/* Right Panel - Login Form */}
      <div className="flex w-full lg:w-1/2 items-center justify-center p-8 bg-background">
        <div className="w-full max-w-md space-y-8">
          {/* Mobile Logo */}
          <div className="lg:hidden flex justify-center mb-8">
            <Link href="/" className="flex items-center gap-3">
              <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-primary">
                <Film className="h-7 w-7 text-primary-foreground" />
              </div>
              <span className="text-2xl font-bold text-foreground">FilmGenX</span>
            </Link>
          </div>

          <div className="space-y-2 text-center lg:text-left">
            <h2 className="text-3xl font-bold text-foreground">欢迎回来</h2>
            <p className="text-muted-foreground">请登录您的账户以继续</p>
          </div>

          {/* Error Message */}
          {error && (
            <div className="rounded-lg border border-destructive/50 bg-destructive/10 px-4 py-3 text-sm text-destructive">
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-6">
            <div className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="email" className="text-foreground">邮箱地址</Label>
                <div className="relative">
                  <Mail className="absolute left-3 top-1/2 h-5 w-5 -translate-y-1/2 text-muted-foreground" />
                  <Input
                    id="email"
                    type="email"
                    placeholder="your@email.com"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    className="pl-10 h-12 bg-card border-border"
                    required
                    disabled={isLoading}
                  />
                </div>
              </div>

              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <Label htmlFor="password" className="text-foreground">密码</Label>
                </div>
                <div className="relative">
                  <Lock className="absolute left-3 top-1/2 h-5 w-5 -translate-y-1/2 text-muted-foreground" />
                  <Input
                    id="password"
                    type={showPassword ? 'text' : 'password'}
                    placeholder="输入您的密码"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    className="pl-10 pr-10 h-12 bg-card border-border"
                    required
                    disabled={isLoading}
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground transition-colors"
                  >
                    {showPassword ? <EyeOff className="h-5 w-5" /> : <Eye className="h-5 w-5" />}
                  </button>
                </div>
              </div>
            </div>

            <div className="flex items-center gap-2">
              <Checkbox
                id="remember"
                checked={rememberMe}
                onCheckedChange={(checked) => setRememberMe(checked as boolean)}
              />
              <Label htmlFor="remember" className="text-sm text-muted-foreground cursor-pointer">
                记住我的登录状态
              </Label>
            </div>

            <Button
              type="submit"
              className="w-full h-12 bg-primary text-primary-foreground hover:bg-primary/90 font-medium"
              disabled={isLoading}
            >
              {isLoading ? (
                <div className="flex items-center gap-2">
                  <div className="h-4 w-4 animate-spin rounded-full border-2 border-primary-foreground border-t-transparent" />
                  <span>登录中...</span>
                </div>
              ) : (
                <div className="flex items-center gap-2">
                  <span>登录</span>
                  <ArrowRight className="h-4 w-4" />
                </div>
              )}
            </Button>
          </form>

          {/* Divider */}
          <div className="relative">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t border-border" />
            </div>
            <div className="relative flex justify-center text-xs uppercase">
              <span className="bg-background px-2 text-muted-foreground">或者</span>
            </div>
          </div>

          {/* Sign Up Link */}
          <p className="text-center text-sm text-muted-foreground">
            还没有账户？{' '}
            <Link href="/register" className="text-primary hover:text-primary/80 font-medium transition-colors">
              立即注册
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}
