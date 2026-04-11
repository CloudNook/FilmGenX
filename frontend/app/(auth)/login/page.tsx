'use client';

import { useState, useEffect, useRef } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { Film, Eye, EyeOff, Mail, Lock, ArrowRight, KeyRound } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Checkbox } from '@/components/ui/checkbox';
import { useAuth } from '@/lib/auth';
import gsap from 'gsap';

export default function LoginPage() {
  const router = useRouter();
  const { login } = useAuth();
  const [showPassword, setShowPassword] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [inviteCode, setInviteCode] = useState('');
  const [rememberMe, setRememberMe] = useState(false);
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
  const footerRef = useRef<HTMLParagraphElement>(null);

  useEffect(() => {
    const ctx = gsap.context(() => {
      const tl = gsap.timeline({ defaults: { ease: 'power3.out' } });

      // Left panel animations
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
        )
        .from(
          footerRef.current,
          {
            opacity: 0,
            duration: 0.5,
          },
          '-=0.2'
        );

      // Right panel animations with stagger
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

  // Animate error shake
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
    setIsLoading(true);

    try {
      await login(email, password, inviteCode);
      // Animate out before navigation
      gsap.to(containerRef.current, {
        x: -100,
        opacity: 0,
        duration: 0.5,
        ease: 'power2.in',
        onComplete: () => router.push('/home'),
      });
    } catch (err: any) {
      setError(err.message || '登录失败，请重试');
      setIsLoading(false);
    }
  };

  const features = [
    'AI 智能剧本创作与优化',
    '自动化分镜生成与调整',
    '角色一致性智能管理',
    '多模态内容协同制作',
  ];

  return (
    <div ref={containerRef} className="flex min-h-screen overflow-hidden">
      {/* Animated Background Gradient */}
      <div className="fixed inset-0 -z-10">
        <div className="absolute inset-0 bg-gradient-to-br from-background via-background to-secondary/30" />
        <div
          className="absolute w-96 h-96 rounded-full opacity-20 blur-3xl"
          style={{
            background: 'linear-gradient(135deg, oklch(0.646 0.222 41.116), oklch(0.6 0.118 184.704))',
            top: '10%',
            left: '20%',
            animation: 'float 8s ease-in-out infinite',
          }}
        />
        <div
          className="absolute w-80 h-80 rounded-full opacity-15 blur-3xl"
          style={{
            background: 'linear-gradient(135deg, oklch(0.398 0.07 227.392), oklch(0.769 0.188 70.08))',
            bottom: '10%',
            right: '20%',
            animation: 'float 10s ease-in-out infinite reverse',
          }}
        />
      </div>

      {/* Left Panel - Branding */}
      <div
        ref={leftPanelRef}
        className="hidden lg:flex lg:w-1/2 flex-col justify-between bg-secondary/50 p-12 relative overflow-hidden"
      >
        {/* Decorative Elements */}
        <div className="absolute top-0 right-0 w-64 h-64 opacity-10">
          <svg viewBox="0 0 200 200" className="w-full h-full">
            <circle cx="100" cy="100" r="80" fill="none" stroke="currentColor" strokeWidth="0.5" className="text-foreground" />
            <circle cx="100" cy="100" r="60" fill="none" stroke="currentColor" strokeWidth="0.5" className="text-foreground" />
            <circle cx="100" cy="100" r="40" fill="none" stroke="currentColor" strokeWidth="0.5" className="text-foreground" />
          </svg>
        </div>

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
            新一代 AI 驱动的
            <br />
            <span className="text-primary relative">
              动画内容生产系统
              <svg className="absolute -bottom-1 left-0 w-full h-2" viewBox="0 0 200 8" preserveAspectRatio="none">
                <path d="M0 4 Q 50 0, 100 4 T 200 4" fill="none" stroke="oklch(0.646 0.222 41.116)" strokeWidth="2" />
              </svg>
            </span>
          </h1>
          <p ref={subtitleRef} className="text-lg text-muted-foreground max-w-md leading-relaxed">
            从剧本到成片的全流程智能化解决方案，让创意无限延伸，让制作更加高效。
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

        <p ref={footerRef} className="text-sm text-muted-foreground relative z-10">
          FilmGenX 2024. 保留所有权利。
        </p>
      </div>

      {/* Right Panel - Login Form */}
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
            <h2 className="text-3xl font-bold text-foreground">欢迎回来</h2>
            <p className="text-muted-foreground">请登录您的账户以继续</p>
          </div>

          {/* Error Message */}
          {error && (
            <div className="rounded-lg border border-destructive/50 bg-destructive/10 px-4 py-3 text-sm text-destructive">
              {error}
            </div>
          )}

          <form ref={formRef} onSubmit={handleSubmit} className="space-y-6">
            <div className="space-y-4">
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
                <Label htmlFor="password" className="text-foreground">密码</Label>
                <div className="relative group">
                  <Lock className="absolute left-3 top-1/2 h-5 w-5 -translate-y-1/2 text-muted-foreground transition-colors group-focus-within:text-primary" />
                  <Input
                    id="password"
                    type={showPassword ? 'text' : 'password'}
                    placeholder="输入您的密码"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    className="pl-10 pr-10 h-12 bg-card border-border transition-all duration-300 group-focus-within:border-primary group-focus-within:shadow-lg group-focus-within:shadow-primary/10"
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

              <div
                ref={(el) => { if (el) inputsRef.current[2] = el; }}
                className="space-y-2"
              >
                <Label htmlFor="invite-code" className="text-foreground">邀请码</Label>
                <div className="relative group">
                  <KeyRound className="absolute left-3 top-1/2 h-5 w-5 -translate-y-1/2 text-muted-foreground transition-colors group-focus-within:text-primary" />
                  <Input
                    id="invite-code"
                    type="text"
                    placeholder="输入邀请码"
                    value={inviteCode}
                    onChange={(e) => setInviteCode(e.target.value)}
                    className="pl-10 h-12 bg-card border-border transition-all duration-300 group-focus-within:border-primary group-focus-within:shadow-lg group-focus-within:shadow-primary/10"
                    disabled={isLoading}
                  />
                </div>
              </div>
            </div>

            <div
              ref={(el) => { if (el) inputsRef.current[3] = el; }}
              className="flex items-center gap-2"
            >
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
              className="w-full h-12 bg-primary text-primary-foreground hover:bg-primary/90 font-medium relative overflow-hidden group"
              disabled={isLoading}
            >
              <span className="relative z-10 flex items-center justify-center gap-2">
                {isLoading ? (
                  <>
                    <div className="h-4 w-4 animate-spin rounded-full border-2 border-primary-foreground border-t-transparent" />
                    <span>登录中...</span>
                  </>
                ) : (
                  <>
                    <span>登录</span>
                    <ArrowRight className="h-4 w-4 transition-transform duration-300 group-hover:translate-x-1" />
                  </>
                )}
              </span>
              {/* Button shine effect */}
              <div className="absolute inset-0 -translate-x-full group-hover:translate-x-full transition-transform duration-700 bg-gradient-to-r from-transparent via-white/20 to-transparent" />
            </Button>
          </form>

          <p className="text-center text-xs text-muted-foreground">
            仅限受邀用户访问
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
