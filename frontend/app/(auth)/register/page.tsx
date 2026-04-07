'use client';

import { useState, useEffect, useRef } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { Film, Eye, EyeOff, Mail, Lock, User, ArrowRight, Sparkles } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { useAuth } from '@/lib/auth';
import gsap from 'gsap';

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

  const containerRef = useRef<HTMLDivElement>(null);
  const leftPanelRef = useRef<HTMLDivElement>(null);
  const rightPanelRef = useRef<HTMLDivElement>(null);
  const logoRef = useRef<HTMLDivElement>(null);
  const titleRef = useRef<HTMLHeadingElement>(null);
  const subtitleRef = useRef<HTMLParagraphElement>(null);
  const featuresRef = useRef<HTMLDivElement>(null);
  const formRef = useRef<HTMLFormElement>(null);
  const headingRef = useRef<HTMLHeadingElement>(null);
  const inputsRef = useRef<HTMLDivElement[]>([]);

  useEffect(() => {
    const ctx = gsap.context(() => {
      const tl = gsap.timeline({ defaults: { ease: 'power3.out' } });

      // Left panel entrance
      tl.from(leftPanelRef.current, {
        x: -100,
        opacity: 0,
        duration: 1,
      })
        .from(
          logoRef.current,
          {
            y: -30,
            opacity: 0,
            duration: 0.8,
          },
          '-=0.6'
        )
        .from(
          titleRef.current,
          {
            y: 30,
            opacity: 0,
            duration: 0.8,
          },
          '-=0.5'
        )
        .from(
          subtitleRef.current,
          {
            y: 20,
            opacity: 0,
            duration: 0.6,
          },
          '-=0.4'
        )
        .from(
          featuresRef.current?.children || [],
          {
            x: -40,
            opacity: 0,
            duration: 0.5,
            stagger: 0.15,
          },
          '-=0.3'
        );

      // Right panel animations
      tl.from(
        rightPanelRef.current,
        {
          x: 100,
          opacity: 0,
          duration: 1,
        },
        '-=1'
      ).from(
        headingRef.current,
        {
          y: 20,
          opacity: 0,
          duration: 0.6,
        },
        '-=0.8'
      );

      // Stagger input animations
      inputsRef.current.forEach((input, i) => {
        if (input) {
          gsap.from(input, {
            x: 40,
            opacity: 0,
            duration: 0.5,
            delay: 0.3 + i * 0.1,
            ease: 'power2.out',
          });
        }
      });
    }, containerRef);

    return () => ctx.revert();
  }, []);

  // Animate error
  useEffect(() => {
    if (error && formRef.current) {
      gsap.fromTo(
        formRef.current,
        { x: -10 },
        {
          x: 0,
          duration: 0.5,
          ease: 'elastic.out(1, 0.3)',
        }
      );
    }
  }, [error]);

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
      // Success animation
      gsap.to(containerRef.current, {
        x: -100,
        opacity: 0,
        duration: 0.5,
        ease: 'power2.in',
        onComplete: () => router.push('/projects'),
      });
    } catch (err: any) {
      setError(err.message || '注册失败，请重试');
      setIsLoading(false);
    }
  };

  const features = [
    '免费开始，无需信用卡',
    '全功能 AI 剧本创作工具',
    '一键生成专业级分镜',
    '7x24 小时云端协作',
  ];

  return (
    <div ref={containerRef} className="flex min-h-screen overflow-hidden">
      {/* Animated Background */}
      <div className="fixed inset-0 -z-10">
        <div className="absolute inset-0 bg-gradient-to-br from-background via-background to-secondary/30" />
        <div
          className="absolute w-96 h-96 rounded-full opacity-20 blur-3xl"
          style={{
            background: 'linear-gradient(135deg, oklch(0.646 0.222 41.116), oklch(0.769 0.188 70.08))',
            top: '20%',
            right: '10%',
            animation: 'float 9s ease-in-out infinite',
          }}
        />
        <div
          className="absolute w-72 h-72 rounded-full opacity-15 blur-3xl"
          style={{
            background: 'linear-gradient(135deg, oklch(0.398 0.07 227.392), oklch(0.646 0.222 41.116))',
            bottom: '15%',
            left: '15%',
            animation: 'float 11s ease-in-out infinite reverse',
          }}
        />
      </div>

      {/* Left Panel - Branding */}
      <div
        ref={leftPanelRef}
        className="hidden lg:flex lg:w-1/2 flex-col justify-between bg-secondary/50 p-12 relative overflow-hidden"
      >
        {/* Decorative Grid Pattern */}
        <div className="absolute inset-0 opacity-5">
          <svg width="100%" height="100%" xmlns="http://www.w3.org/2000/svg">
            <defs>
              <pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse">
                <path d="M 40 0 L 0 0 0 40" fill="none" stroke="currentColor" strokeWidth="1" />
              </pattern>
            </defs>
            <rect width="100%" height="100%" fill="url(#grid)" />
          </svg>
        </div>

        {/* Floating Particles */}
        <div className="absolute top-1/4 right-1/4 w-2 h-2 rounded-full bg-primary/30 animate-pulse" />
        <div className="absolute top-2/3 left-1/3 w-3 h-3 rounded-full bg-primary/20 animate-pulse" style={{ animationDelay: '0.5s' }} />
        <div className="absolute top-1/3 left-2/3 w-2 h-2 rounded-full bg-primary/25 animate-pulse" style={{ animationDelay: '1s' }} />

        <div ref={logoRef}>
          <Link href="/" className="flex items-center gap-3 group">
            <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-primary relative overflow-hidden">
              <Film className="h-7 w-7 text-primary-foreground relative z-10" />
              <div className="absolute inset-0 bg-gradient-to-r from-primary to-primary/80 opacity-0 group-hover:opacity-100 transition-opacity duration-300" />
            </div>
            <span className="text-2xl font-bold text-foreground">FilmGenX</span>
          </Link>
        </div>

        <div className="space-y-6 relative z-10">
          <h1 ref={titleRef} className="text-4xl font-bold leading-tight text-foreground text-balance">
            开始您的
            <br />
            <span className="text-primary relative inline-flex items-center gap-2">
              AI 动画创作之旅
              <Sparkles className="h-6 w-6 inline-block animate-pulse" />
            </span>
          </h1>
          <p ref={subtitleRef} className="text-lg text-muted-foreground max-w-md leading-relaxed">
            注册账户，体验从剧本到成片的全流程 AI 智能制作。
          </p>

          <div ref={featuresRef} className="space-y-4 pt-4">
            {features.map((feature, index) => (
              <div key={index} className="flex items-center gap-3 group cursor-pointer">
                <div className="flex h-6 w-6 items-center justify-center rounded-full bg-primary relative overflow-hidden">
                  <div className="h-2 w-2 rounded-full bg-primary-foreground relative z-10" />
                  <div className="absolute inset-0 bg-gradient-to-r from-primary to-primary/70 scale-0 group-hover:scale-100 transition-transform duration-300 origin-left" />
                </div>
                <span className="text-foreground group-hover:text-primary transition-colors duration-300">{feature}</span>
              </div>
            ))}
          </div>
        </div>

        <p className="text-sm text-muted-foreground relative z-10">
          FilmGenX 2024. 保留所有权利。
        </p>
      </div>

      {/* Right Panel - Register Form */}
      <div ref={rightPanelRef} className="flex w-full lg:w-1/2 items-center justify-center p-8 relative">
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

          <div ref={headingRef} className="space-y-2 text-center lg:text-left">
            <h2 className="text-3xl font-bold text-foreground">创建账户</h2>
            <p className="text-muted-foreground">填写以下信息完成注册</p>
          </div>

          {/* Error Message */}
          {error && (
            <div className="rounded-lg border border-destructive/50 bg-destructive/10 px-4 py-3 text-sm text-destructive animate-shake-gsap">
              {error}
            </div>
          )}

          <form ref={formRef} onSubmit={handleSubmit} className="space-y-5">
            <div
              ref={(el) => { if (el) inputsRef.current[0] = el; }}
              className="space-y-2"
            >
              <Label htmlFor="email" className="text-foreground">邮箱地址</Label>
              <div className="relative group">
                <Mail className="absolute left-3 top-1/2 h-5 w-5 -translate-y-1/2 text-muted-foreground transition-colors group-focus-within:text-primary" />
                <Input
                  id="email"
                  type="email"
                  placeholder="your@email.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="pl-10 h-12 bg-card border-border transition-all duration-300 group-focus-within:border-primary group-focus-within:shadow-lg group-focus-within:shadow-primary/10"
                  required
                  disabled={isLoading}
                />
              </div>
            </div>

            <div
              ref={(el) => { if (el) inputsRef.current[1] = el; }}
              className="space-y-2"
            >
              <Label htmlFor="username" className="text-foreground">用户名</Label>
              <div className="relative group">
                <User className="absolute left-3 top-1/2 h-5 w-5 -translate-y-1/2 text-muted-foreground transition-colors group-focus-within:text-primary" />
                <Input
                  id="username"
                  type="text"
                  placeholder="输入您的用户名"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  className="pl-10 h-12 bg-card border-border transition-all duration-300 group-focus-within:border-primary group-focus-within:shadow-lg group-focus-within:shadow-primary/10"
                  required
                  disabled={isLoading}
                  minLength={2}
                  maxLength={50}
                />
              </div>
            </div>

            <div
              ref={(el) => { if (el) inputsRef.current[2] = el; }}
              className="space-y-2"
            >
              <Label htmlFor="password" className="text-foreground">密码</Label>
              <div className="relative group">
                <Lock className="absolute left-3 top-1/2 h-5 w-5 -translate-y-1/2 text-muted-foreground transition-colors group-focus-within:text-primary" />
                <Input
                  id="password"
                  type={showPassword ? 'text' : 'password'}
                  placeholder="至少 6 位字符"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="pl-10 pr-10 h-12 bg-card border-border transition-all duration-300 group-focus-within:border-primary group-focus-within:shadow-lg group-focus-within:shadow-primary/10"
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

            <div
              ref={(el) => { if (el) inputsRef.current[3] = el; }}
              className="space-y-2"
            >
              <Label htmlFor="confirmPassword" className="text-foreground">确认密码</Label>
              <div className="relative group">
                <Lock className="absolute left-3 top-1/2 h-5 w-5 -translate-y-1/2 text-muted-foreground transition-colors group-focus-within:text-primary" />
                <Input
                  id="confirmPassword"
                  type={showPassword ? 'text' : 'password'}
                  placeholder="再次输入密码"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  className="pl-10 h-12 bg-card border-border transition-all duration-300 group-focus-within:border-primary group-focus-within:shadow-lg group-focus-within:shadow-primary/10"
                  required
                  disabled={isLoading}
                  minLength={6}
                />
              </div>
            </div>

            <Button
              type="submit"
              className="w-full h-12 bg-primary text-primary-foreground hover:bg-primary/90 font-medium relative overflow-hidden group"
              disabled={isLoading}
            >
              <span className="relative z-10 flex items-center justify-center gap-2">
                {isLoading ? (
                  <>
                    <div className="h-4 w-4 animate-spin rounded-full border-2 border-primary-foreground border-t-transparent" />
                    <span>注册中...</span>
                  </>
                ) : (
                  <>
                    <span>注册</span>
                    <ArrowRight className="h-4 w-4 transition-transform duration-300 group-hover:translate-x-1" />
                  </>
                )}
              </span>
              {/* Button shine effect */}
              <div className="absolute inset-0 -translate-x-full group-hover:translate-x-full transition-transform duration-700 bg-gradient-to-r from-transparent via-white/20 to-transparent" />
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

          {/* Login Link */}
          <p className="text-center text-sm text-muted-foreground">
            已有账户？{' '}
            <Link href="/login" className="text-primary hover:text-primary/80 font-medium transition-colors relative group">
              立即登录
              <span className="absolute -bottom-0.5 left-0 w-0 h-0.5 bg-primary transition-all duration-300 group-hover:w-full" />
            </Link>
          </p>
        </div>
      </div>

      <style jsx global>{`
        @keyframes float {
          0%, 100% { transform: translate(0, 0) scale(1); }
          50% { transform: translate(30px, -30px) scale(1.1); }
        }
      `}</style>
    </div>
  );
}
