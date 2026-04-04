'use client';

import { useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { Film, Eye, EyeOff, Mail, Lock, User, ArrowRight } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { useAuth } from '@/lib/auth';

export default function RegisterPage() {
  const router = useRouter();
  const { register } = useAuth();
  const [showPassword, setShowPassword] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [email, setEmail] = useState('');
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [error, setError] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    if (password !== confirmPassword) {
      setError('两次输入的密码不一致');
      return;
    }
    if (password.length < 6) {
      setError('密码长度不能少于 6 位');
      return;
    }

    setIsLoading(true);
    try {
      await register(email, username, password);
      router.push('/projects');
    } catch (err: any) {
      setError(err.message || '注册失败，请重试');
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
            开始您的
            <br />
            <span className="text-primary">AI 动画创作之旅</span>
          </h1>
          <p className="text-lg text-muted-foreground max-w-md leading-relaxed">
            注册账户，体验从剧本到成片的全流程 AI 智能制作。
          </p>
        </div>

        <p className="text-sm text-muted-foreground">
          FilmGenX 2024. 保留所有权利。
        </p>
      </div>

      {/* Right Panel - Register Form */}
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
            <h2 className="text-3xl font-bold text-foreground">创建账户</h2>
            <p className="text-muted-foreground">填写以下信息完成注册</p>
          </div>

          {/* Error Message */}
          {error && (
            <div className="rounded-lg border border-destructive/50 bg-destructive/10 px-4 py-3 text-sm text-destructive">
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-5">
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
              <Label htmlFor="username" className="text-foreground">用户名</Label>
              <div className="relative">
                <User className="absolute left-3 top-1/2 h-5 w-5 -translate-y-1/2 text-muted-foreground" />
                <Input
                  id="username"
                  type="text"
                  placeholder="输入您的用户名"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  className="pl-10 h-12 bg-card border-border"
                  required
                  disabled={isLoading}
                  minLength={2}
                  maxLength={50}
                />
              </div>
            </div>

            <div className="space-y-2">
              <Label htmlFor="password" className="text-foreground">密码</Label>
              <div className="relative">
                <Lock className="absolute left-3 top-1/2 h-5 w-5 -translate-y-1/2 text-muted-foreground" />
                <Input
                  id="password"
                  type={showPassword ? 'text' : 'password'}
                  placeholder="至少 6 位字符"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="pl-10 pr-10 h-12 bg-card border-border"
                  required
                  disabled={isLoading}
                  minLength={6}
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

            <div className="space-y-2">
              <Label htmlFor="confirmPassword" className="text-foreground">确认密码</Label>
              <div className="relative">
                <Lock className="absolute left-3 top-1/2 h-5 w-5 -translate-y-1/2 text-muted-foreground" />
                <Input
                  id="confirmPassword"
                  type={showPassword ? 'text' : 'password'}
                  placeholder="再次输入密码"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  className="pl-10 h-12 bg-card border-border"
                  required
                  disabled={isLoading}
                  minLength={6}
                />
              </div>
            </div>

            <Button
              type="submit"
              className="w-full h-12 bg-primary text-primary-foreground hover:bg-primary/90 font-medium"
              disabled={isLoading}
            >
              {isLoading ? (
                <div className="flex items-center gap-2">
                  <div className="h-4 w-4 animate-spin rounded-full border-2 border-primary-foreground border-t-transparent" />
                  <span>注册中...</span>
                </div>
              ) : (
                <div className="flex items-center gap-2">
                  <span>注册</span>
                  <ArrowRight className="h-4 w-4" />
                </div>
              )}
            </Button>
          </form>

          {/* Login Link */}
          <p className="text-center text-sm text-muted-foreground">
            已有账户？{' '}
            <Link href="/login" className="text-primary hover:text-primary/80 font-medium transition-colors">
              立即登录
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}
