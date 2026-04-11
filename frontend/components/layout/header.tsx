'use client';

import { useRouter } from 'next/navigation';
import { Bell, Search, HelpCircle, LogOut, User, Settings } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { useAuth } from '@/lib/auth';

interface HeaderProps {
  title?: string;
  description?: string;
  showSearch?: boolean;
  breadcrumbs?: Array<{ label: string; href?: string }>;
}

export function Header({ title, description, showSearch = true, breadcrumbs }: HeaderProps) {
  const { user, logout } = useAuth();
  const router = useRouter();

  const handleLogout = () => {
    logout();
    router.push('/login');
  };

  const displayName = user?.username || '未登录';
  const displayEmail = user?.email || '';
  const avatarFallback = displayName.slice(0, 2);

  return (
    <header className="flex h-16 items-center justify-between border-b border-border bg-card px-6">
      {/* Left Section */}
      <div className="flex items-center gap-4">
        {breadcrumbs && breadcrumbs.length > 0 && (
          <nav className="flex items-center gap-1 text-sm">
            {breadcrumbs.map((item, index) => (
              <span key={index} className="flex items-center gap-1">
                {index > 0 && <span className="text-muted-foreground">/</span>}
                {item.href ? (
                  <a
                    href={item.href}
                    className="text-muted-foreground hover:text-foreground transition-colors"
                  >
                    {item.label}
                  </a>
                ) : (
                  <span className="text-foreground font-medium">{item.label}</span>
                )}
              </span>
            ))}
          </nav>
        )}
        {title && !breadcrumbs && (
          <div className="min-w-0">
            <h1 className="text-xl font-semibold text-foreground">{title}</h1>
            {description ? (
              <p className="mt-1 max-w-2xl truncate text-sm text-muted-foreground">{description}</p>
            ) : null}
          </div>
        )}
      </div>

      {/* Right Section */}
      <div className="flex items-center gap-3">
        {/* Search */}
        {showSearch && (
          <div className="relative w-64">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              type="search"
              placeholder="搜索项目、镜头、角色..."
              className="pl-9 bg-secondary border-border"
            />
          </div>
        )}

        {/* Help */}
        <Button variant="ghost" size="icon" className="text-muted-foreground hover:text-foreground">
          <HelpCircle className="h-5 w-5" />
        </Button>

        {/* Notifications */}
        <Button variant="ghost" size="icon" className="relative text-muted-foreground hover:text-foreground">
          <Bell className="h-5 w-5" />
          <span className="absolute right-1.5 top-1.5 flex h-2 w-2">
            <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-primary opacity-75"></span>
            <span className="relative inline-flex h-2 w-2 rounded-full bg-primary"></span>
          </span>
        </Button>

        {/* User Menu */}
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" className="flex items-center gap-2 pl-2 pr-3">
              <Avatar className="h-8 w-8">
                <AvatarImage src={user?.avatar_url || undefined} alt={displayName} />
                <AvatarFallback className="bg-primary text-primary-foreground text-sm">
                  {avatarFallback}
                </AvatarFallback>
              </Avatar>
              <span className="text-sm font-medium text-foreground">{displayName}</span>
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-56">
            <DropdownMenuLabel>
              <div className="flex flex-col">
                <span>{displayName}</span>
                <span className="text-xs font-normal text-muted-foreground">{displayEmail}</span>
              </div>
            </DropdownMenuLabel>
            <DropdownMenuSeparator />
            <DropdownMenuItem onClick={() => router.push('/settings')}>
              <User className="mr-2 h-4 w-4" />
              个人资料
            </DropdownMenuItem>
            <DropdownMenuItem onClick={() => router.push('/settings')}>
              <Settings className="mr-2 h-4 w-4" />
              账户设置
            </DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem className="text-destructive" onClick={handleLogout}>
              <LogOut className="mr-2 h-4 w-4" />
              退出登录
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </header>
  );
}
