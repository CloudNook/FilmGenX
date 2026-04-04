"use client";

import { useCallback, useRef, useState } from "react";
import { AppLayout } from "@/components/layout";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Slider } from "@/components/ui/slider";
import { Badge } from "@/components/ui/badge";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Separator } from "@/components/ui/separator";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  User,
  Bell,
  Palette,
  Cpu,
  Shield,
  HardDrive,
  Zap,
  Monitor,
  Moon,
  Sun,
  Camera,
  Save,
  RotateCcw,
  Key,
  CreditCard,
  CheckCircle2,
  Loader2,
} from "lucide-react";
import { useAuth } from "@/lib/auth";
import { authApi } from "@/lib/api";

export default function SettingsPage() {
  const { user, refreshUser } = useAuth();
  const [activeTab, setActiveTab] = useState("profile");
  const [saving, setSaving] = useState(false);
  const [saveMessage, setSaveMessage] = useState<{ type: "success" | "error"; text: string } | null>(null);
  const avatarInputRef = useRef<HTMLInputElement>(null);
  const [uploadingAvatar, setUploadingAvatar] = useState(false);

  const [username, setUsername] = useState(user?.username || "");
  const [email] = useState(user?.email || "");

  // 同步用户数据到表单
  const [prevUsername, setPrevUsername] = useState(user?.username || "");
  if (user && user.username !== prevUsername) {
    setPrevUsername(user.username);
    setUsername(user.username);
  }

  const [notifications, setNotifications] = useState({
    email: true,
    push: true,
    taskComplete: true,
    weeklyReport: false,
    mentions: true,
  });
  const [appearance, setAppearance] = useState({
    theme: "dark",
    accentColor: "gold",
    fontSize: 14,
    compactMode: false,
  });
  const [aiSettings, setAiSettings] = useState({
    autoSave: true,
    qualityPreset: "high",
    parallelTasks: 3,
    gpuAcceleration: true,
    cacheSize: 50,
  });

  const handleAvatarUpload = useCallback(async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploadingAvatar(true);
    setSaveMessage(null);
    try {
      await authApi.uploadAvatar(file);
      await refreshUser();
      setSaveMessage({ type: "success", text: "头像已更新" });
    } catch (err) {
      setSaveMessage({ type: "error", text: err instanceof Error ? err.message : "上传失败" });
    } finally {
      setUploadingAvatar(false);
    }
  }, [refreshUser]);

  const handleSave = useCallback(async () => {
    setSaving(true);
    setSaveMessage(null);
    try {
      const data: { username?: string } = {};
      if (username !== user?.username) data.username = username;
      if (Object.keys(data).length > 0) {
        await authApi.updateMe(data);
        await refreshUser();
      }
      setSaveMessage({ type: "success", text: "设置已保存" });
    } catch (err) {
      setSaveMessage({ type: "error", text: err instanceof Error ? err.message : "保存失败" });
    } finally {
      setSaving(false);
    }
  }, [username, user?.username, refreshUser]);

  const handleReset = useCallback(() => {
    setUsername(user?.username || "");
    setSaveMessage(null);
  }, [user?.username]);

  const avatarFallback = (user?.username || "U").slice(0, 2).toUpperCase();

  return (
    <AppLayout>
      <div className="flex-1 overflow-auto">
        <div className="max-w-5xl mx-auto p-6">
          {/* Header */}
          <div className="mb-8">
            <h1 className="text-2xl font-bold text-foreground">全局设置</h1>
            <p className="text-muted-foreground mt-1">
              管理您的账户、偏好设置和系统配置
            </p>
          </div>

          <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-6">
            <TabsList className="bg-secondary/50 p-1">
              <TabsTrigger value="profile" className="gap-2">
                <User className="h-4 w-4" />
                个人资料
              </TabsTrigger>
              <TabsTrigger value="notifications" className="gap-2">
                <Bell className="h-4 w-4" />
                通知
              </TabsTrigger>
              <TabsTrigger value="appearance" className="gap-2">
                <Palette className="h-4 w-4" />
                外观
              </TabsTrigger>
              <TabsTrigger value="ai" className="gap-2">
                <Cpu className="h-4 w-4" />
                AI 配置
              </TabsTrigger>
              <TabsTrigger value="security" className="gap-2">
                <Shield className="h-4 w-4" />
                安全
              </TabsTrigger>
              <TabsTrigger value="storage" className="gap-2">
                <HardDrive className="h-4 w-4" />
                存储
              </TabsTrigger>
            </TabsList>

            {/* Profile Tab */}
            <TabsContent value="profile" className="space-y-6">
              <Card className="bg-card border-border">
                <CardHeader>
                  <CardTitle>个人信息</CardTitle>
                  <CardDescription>更新您的个人资料和账户信息</CardDescription>
                </CardHeader>
                <CardContent className="space-y-6">
                  <div className="flex items-center gap-6">
                    <Avatar className="h-24 w-24">
                      <AvatarImage src={user?.avatar_url || undefined} alt={user?.username} />
                      <AvatarFallback className="bg-primary/20 text-primary text-2xl">
                        {avatarFallback}
                      </AvatarFallback>
                    </Avatar>
                    <div className="space-y-2">
                      <input
                        ref={avatarInputRef}
                        type="file"
                        accept="image/jpeg,image/png,image/webp,image/gif"
                        className="hidden"
                        onChange={handleAvatarUpload}
                      />
                      <Button
                        variant="outline"
                        size="sm"
                        className="gap-2"
                        disabled={uploadingAvatar}
                        onClick={() => avatarInputRef.current?.click()}
                      >
                        {uploadingAvatar ? (
                          <Loader2 className="h-4 w-4 animate-spin" />
                        ) : (
                          <Camera className="h-4 w-4" />
                        )}
                        {uploadingAvatar ? "上传中..." : "更换头像"}
                      </Button>
                      <p className="text-xs text-muted-foreground">
                        支持 JPG、PNG、WebP、GIF 格式，最大 5MB
                      </p>
                    </div>
                  </div>

                  <Separator />

                  <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label htmlFor="username">用户名</Label>
                      <Input
                        id="username"
                        value={username}
                        onChange={(e) => setUsername(e.target.value)}
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="email">邮箱</Label>
                      <Input id="email" type="email" value={email} disabled className="opacity-60" />
                    </div>
                  </div>
                </CardContent>
              </Card>
            </TabsContent>

            {/* Notifications Tab */}
            <TabsContent value="notifications" className="space-y-6">
              <Card className="bg-card border-border">
                <CardHeader>
                  <CardTitle>通知偏好</CardTitle>
                  <CardDescription>选择您希望接收的通知类型</CardDescription>
                </CardHeader>
                <CardContent className="space-y-6">
                  <div className="space-y-4">
                    <div className="flex items-center justify-between">
                      <div className="space-y-0.5">
                        <Label>邮件通知</Label>
                        <p className="text-sm text-muted-foreground">
                          接收重要更新和项目状态变更的邮件通知
                        </p>
                      </div>
                      <Switch
                        checked={notifications.email}
                        onCheckedChange={(checked) =>
                          setNotifications({ ...notifications, email: checked })
                        }
                      />
                    </div>

                    <Separator />

                    <div className="flex items-center justify-between">
                      <div className="space-y-0.5">
                        <Label>推送通知</Label>
                        <p className="text-sm text-muted-foreground">
                          在浏览器中接收实时推送通知
                        </p>
                      </div>
                      <Switch
                        checked={notifications.push}
                        onCheckedChange={(checked) =>
                          setNotifications({ ...notifications, push: checked })
                        }
                      />
                    </div>

                    <Separator />

                    <div className="flex items-center justify-between">
                      <div className="space-y-0.5">
                        <Label>任务完成通知</Label>
                        <p className="text-sm text-muted-foreground">
                          当 AI 任务完成时收到通知
                        </p>
                      </div>
                      <Switch
                        checked={notifications.taskComplete}
                        onCheckedChange={(checked) =>
                          setNotifications({ ...notifications, taskComplete: checked })
                        }
                      />
                    </div>

                    <Separator />

                    <div className="flex items-center justify-between">
                      <div className="space-y-0.5">
                        <Label>@提及通知</Label>
                        <p className="text-sm text-muted-foreground">
                          当有人在评论中提及您时收到通知
                        </p>
                      </div>
                      <Switch
                        checked={notifications.mentions}
                        onCheckedChange={(checked) =>
                          setNotifications({ ...notifications, mentions: checked })
                        }
                      />
                    </div>

                    <Separator />

                    <div className="flex items-center justify-between">
                      <div className="space-y-0.5">
                        <Label>每周报告</Label>
                        <p className="text-sm text-muted-foreground">
                          每周接收项目进度和使用情况报告
                        </p>
                      </div>
                      <Switch
                        checked={notifications.weeklyReport}
                        onCheckedChange={(checked) =>
                          setNotifications({ ...notifications, weeklyReport: checked })
                        }
                      />
                    </div>
                  </div>
                </CardContent>
              </Card>
            </TabsContent>

            {/* Appearance Tab */}
            <TabsContent value="appearance" className="space-y-6">
              <Card className="bg-card border-border">
                <CardHeader>
                  <CardTitle>主题设置</CardTitle>
                  <CardDescription>自定义应用的外观和显示方式</CardDescription>
                </CardHeader>
                <CardContent className="space-y-6">
                  <div className="space-y-3">
                    <Label>颜色主题</Label>
                    <div className="grid grid-cols-3 gap-4">
                      {[
                        { id: "dark", name: "深色", icon: Moon },
                        { id: "light", name: "浅色", icon: Sun },
                        { id: "system", name: "跟随系统", icon: Monitor },
                      ].map((theme) => (
                        <button
                          key={theme.id}
                          onClick={() => setAppearance({ ...appearance, theme: theme.id })}
                          className={`flex flex-col items-center gap-2 p-4 rounded-lg border transition-colors ${
                            appearance.theme === theme.id
                              ? "bg-primary/20 border-primary"
                              : "bg-secondary/30 border-border hover:border-primary/50"
                          }`}
                        >
                          <theme.icon className="h-6 w-6" />
                          <span className="text-sm">{theme.name}</span>
                        </button>
                      ))}
                    </div>
                  </div>

                  <Separator />

                  <div className="space-y-3">
                    <Label>强调色</Label>
                    <div className="flex gap-3">
                      {[
                        { id: "gold", color: "bg-[#f0a500]" },
                        { id: "blue", color: "bg-blue-500" },
                        { id: "green", color: "bg-green-500" },
                        { id: "purple", color: "bg-purple-500" },
                        { id: "red", color: "bg-red-500" },
                      ].map((color) => (
                        <button
                          key={color.id}
                          onClick={() => setAppearance({ ...appearance, accentColor: color.id })}
                          className={`h-8 w-8 rounded-full ${color.color} transition-transform ${
                            appearance.accentColor === color.id
                              ? "ring-2 ring-white ring-offset-2 ring-offset-background scale-110"
                              : "hover:scale-105"
                          }`}
                        />
                      ))}
                    </div>
                  </div>

                  <Separator />

                  <div className="space-y-3">
                    <div className="flex items-center justify-between">
                      <Label>字体大小</Label>
                      <span className="text-sm text-muted-foreground">{appearance.fontSize}px</span>
                    </div>
                    <Slider
                      value={[appearance.fontSize]}
                      onValueChange={([value]) => setAppearance({ ...appearance, fontSize: value })}
                      min={12}
                      max={18}
                      step={1}
                      className="w-full"
                    />
                  </div>

                  <Separator />

                  <div className="flex items-center justify-between">
                    <div className="space-y-0.5">
                      <Label>紧凑模式</Label>
                      <p className="text-sm text-muted-foreground">
                        减少界面元素的间距，显示更多内容
                      </p>
                    </div>
                    <Switch
                      checked={appearance.compactMode}
                      onCheckedChange={(checked) =>
                        setAppearance({ ...appearance, compactMode: checked })
                      }
                    />
                  </div>
                </CardContent>
              </Card>

              <Card className="bg-card border-border">
                <CardHeader>
                  <CardTitle>语言和地区</CardTitle>
                  <CardDescription>设置您的语言和时区偏好</CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label>语言</Label>
                      <Select defaultValue="zh-CN">
                        <SelectTrigger>
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="zh-CN">简体中文</SelectItem>
                          <SelectItem value="zh-TW">繁體中文</SelectItem>
                          <SelectItem value="en-US">English</SelectItem>
                          <SelectItem value="ja-JP">日本語</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                    <div className="space-y-2">
                      <Label>时区</Label>
                      <Select defaultValue="Asia/Shanghai">
                        <SelectTrigger>
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="Asia/Shanghai">中国标准时间 (UTC+8)</SelectItem>
                          <SelectItem value="Asia/Tokyo">日本标准时间 (UTC+9)</SelectItem>
                          <SelectItem value="America/New_York">美国东部时间 (UTC-5)</SelectItem>
                          <SelectItem value="Europe/London">格林威治时间 (UTC+0)</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </TabsContent>

            {/* AI Configuration Tab */}
            <TabsContent value="ai" className="space-y-6">
              <Card className="bg-card border-border">
                <CardHeader>
                  <CardTitle>AI 生成设置</CardTitle>
                  <CardDescription>配置 AI 生成的质量和性能参数</CardDescription>
                </CardHeader>
                <CardContent className="space-y-6">
                  <div className="space-y-3">
                    <Label>质量预设</Label>
                    <Select
                      value={aiSettings.qualityPreset}
                      onValueChange={(value) =>
                        setAiSettings({ ...aiSettings, qualityPreset: value })
                      }
                    >
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="draft">草稿模式 - 快速预览</SelectItem>
                        <SelectItem value="standard">标准模式 - 平衡质量与速度</SelectItem>
                        <SelectItem value="high">高质量模式 - 最佳效果</SelectItem>
                        <SelectItem value="ultra">超高清模式 - 4K 输出</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>

                  <Separator />

                  <div className="space-y-3">
                    <div className="flex items-center justify-between">
                      <Label>并行任务数</Label>
                      <span className="text-sm text-muted-foreground">
                        {aiSettings.parallelTasks} 个任务
                      </span>
                    </div>
                    <Slider
                      value={[aiSettings.parallelTasks]}
                      onValueChange={([value]) =>
                        setAiSettings({ ...aiSettings, parallelTasks: value })
                      }
                      min={1}
                      max={5}
                      step={1}
                      className="w-full"
                    />
                    <p className="text-xs text-muted-foreground">
                      更多并行任务可以加快处理速度，但会消耗更多资源
                    </p>
                  </div>

                  <Separator />

                  <div className="flex items-center justify-between">
                    <div className="space-y-0.5">
                      <Label className="flex items-center gap-2">
                        <Zap className="h-4 w-4 text-primary" />
                        GPU 加速
                      </Label>
                      <p className="text-sm text-muted-foreground">
                        使用 GPU 加速 AI 计算，大幅提升处理速度
                      </p>
                    </div>
                    <Switch
                      checked={aiSettings.gpuAcceleration}
                      onCheckedChange={(checked) =>
                        setAiSettings({ ...aiSettings, gpuAcceleration: checked })
                      }
                    />
                  </div>

                  <Separator />

                  <div className="flex items-center justify-between">
                    <div className="space-y-0.5">
                      <Label>自动保存</Label>
                      <p className="text-sm text-muted-foreground">
                        自动保存 AI 生成的中间结果
                      </p>
                    </div>
                    <Switch
                      checked={aiSettings.autoSave}
                      onCheckedChange={(checked) =>
                        setAiSettings({ ...aiSettings, autoSave: checked })
                      }
                    />
                  </div>
                </CardContent>
              </Card>

              <Card className="bg-card border-border">
                <CardHeader>
                  <CardTitle>模型配置</CardTitle>
                  <CardDescription>选择用于不同任务的 AI 模型</CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label>剧本生成模型</Label>
                      <Select defaultValue="gpt-4">
                        <SelectTrigger>
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="gpt-4">GPT-4 Turbo</SelectItem>
                          <SelectItem value="claude-3">Claude 3 Opus</SelectItem>
                          <SelectItem value="gemini">Gemini Pro</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                    <div className="space-y-2">
                      <Label>图像生成模型</Label>
                      <Select defaultValue="sdxl">
                        <SelectTrigger>
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="sdxl">Stable Diffusion XL</SelectItem>
                          <SelectItem value="dalle-3">DALL-E 3</SelectItem>
                          <SelectItem value="midjourney">Midjourney V6</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                    <div className="space-y-2">
                      <Label>视频生成模型</Label>
                      <Select defaultValue="runway">
                        <SelectTrigger>
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="runway">Runway Gen-3</SelectItem>
                          <SelectItem value="pika">Pika Labs</SelectItem>
                          <SelectItem value="sora">Sora</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                    <div className="space-y-2">
                      <Label>语音合成模型</Label>
                      <Select defaultValue="eleven">
                        <SelectTrigger>
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="eleven">ElevenLabs</SelectItem>
                          <SelectItem value="azure">Azure TTS</SelectItem>
                          <SelectItem value="bark">Bark</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </TabsContent>

            {/* Security Tab */}
            <TabsContent value="security" className="space-y-6">
              <Card className="bg-card border-border">
                <CardHeader>
                  <CardTitle>密码和认证</CardTitle>
                  <CardDescription>管理您的登录安全设置</CardDescription>
                </CardHeader>
                <CardContent className="space-y-6">
                  <div className="flex items-center justify-between p-4 bg-secondary/30 rounded-lg">
                    <div className="flex items-center gap-4">
                      <div className="h-10 w-10 bg-primary/20 rounded-lg flex items-center justify-center">
                        <Key className="h-5 w-5 text-primary" />
                      </div>
                      <div>
                        <h4 className="font-medium">密码</h4>
                        <p className="text-sm text-muted-foreground">上次修改：30 天前</p>
                      </div>
                    </div>
                    <Button variant="outline" size="sm">
                      修改密码
                    </Button>
                  </div>

                  <div className="flex items-center justify-between p-4 bg-secondary/30 rounded-lg">
                    <div className="flex items-center gap-4">
                      <div className="h-10 w-10 bg-success/20 rounded-lg flex items-center justify-center">
                        <Shield className="h-5 w-5 text-success" />
                      </div>
                      <div>
                        <h4 className="font-medium">双因素认证</h4>
                        <p className="text-sm text-muted-foreground">已启用 - 使用 Authenticator</p>
                      </div>
                    </div>
                    <Badge className="bg-success/20 text-success border-success/30">已启用</Badge>
                  </div>
                </CardContent>
              </Card>

              <Card className="bg-card border-border">
                <CardHeader>
                  <CardTitle>登录历史</CardTitle>
                  <CardDescription>查看您的近期登录记录</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="space-y-3">
                    {[
                      { device: "MacBook Pro", location: "北京, 中国", time: "刚刚", current: true },
                      { device: "iPhone 15", location: "北京, 中国", time: "2小时前", current: false },
                      { device: "Windows PC", location: "上海, 中国", time: "昨天", current: false },
                    ].map((session, index) => (
                      <div
                        key={index}
                        className="flex items-center justify-between p-3 bg-secondary/20 rounded-lg"
                      >
                        <div className="flex items-center gap-3">
                          <Monitor className="h-5 w-5 text-muted-foreground" />
                          <div>
                            <div className="flex items-center gap-2">
                              <span className="font-medium">{session.device}</span>
                              {session.current && (
                                <Badge variant="outline" className="text-xs">当前设备</Badge>
                              )}
                            </div>
                            <p className="text-sm text-muted-foreground">
                              {session.location} · {session.time}
                            </p>
                          </div>
                        </div>
                        {!session.current && (
                          <Button variant="ghost" size="sm" className="text-destructive">
                            注销
                          </Button>
                        )}
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            </TabsContent>

            {/* Storage Tab */}
            <TabsContent value="storage" className="space-y-6">
              <Card className="bg-card border-border">
                <CardHeader>
                  <CardTitle>存储使用情况</CardTitle>
                  <CardDescription>查看您的存储空间使用详情</CardDescription>
                </CardHeader>
                <CardContent className="space-y-6">
                  <div className="space-y-2">
                    <div className="flex items-center justify-between text-sm">
                      <span>已使用 156 GB / 500 GB</span>
                      <span className="text-muted-foreground">31%</span>
                    </div>
                    <div className="h-3 bg-secondary rounded-full overflow-hidden">
                      <div
                        className="h-full bg-primary rounded-full"
                        style={{ width: "31%" }}
                      />
                    </div>
                  </div>

                  <div className="grid grid-cols-2 gap-4">
                    {[
                      { name: "项目文件", size: "89 GB", percent: 57, color: "bg-primary" },
                      { name: "视频渲染", size: "42 GB", percent: 27, color: "bg-info" },
                      { name: "素材库", size: "18 GB", percent: 12, color: "bg-success" },
                      { name: "其他", size: "7 GB", percent: 4, color: "bg-muted" },
                    ].map((item) => (
                      <div key={item.name} className="p-4 bg-secondary/30 rounded-lg">
                        <div className="flex items-center justify-between mb-2">
                          <span className="text-sm font-medium">{item.name}</span>
                          <span className="text-sm text-muted-foreground">{item.size}</span>
                        </div>
                        <div className="h-1.5 bg-secondary rounded-full overflow-hidden">
                          <div
                            className={`h-full ${item.color} rounded-full`}
                            style={{ width: `${item.percent}%` }}
                          />
                        </div>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>

              <Card className="bg-card border-border">
                <CardHeader>
                  <CardTitle>缓存管理</CardTitle>
                  <CardDescription>管理本地缓存和临时文件</CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="flex items-center justify-between p-4 bg-secondary/30 rounded-lg">
                    <div>
                      <h4 className="font-medium">AI 模型缓存</h4>
                      <p className="text-sm text-muted-foreground">12.5 GB</p>
                    </div>
                    <Button variant="outline" size="sm">
                      清除
                    </Button>
                  </div>
                  <div className="flex items-center justify-between p-4 bg-secondary/30 rounded-lg">
                    <div>
                      <h4 className="font-medium">预览缓存</h4>
                      <p className="text-sm text-muted-foreground">3.2 GB</p>
                    </div>
                    <Button variant="outline" size="sm">
                      清除
                    </Button>
                  </div>
                  <div className="flex items-center justify-between p-4 bg-secondary/30 rounded-lg">
                    <div>
                      <h4 className="font-medium">临时文件</h4>
                      <p className="text-sm text-muted-foreground">856 MB</p>
                    </div>
                    <Button variant="outline" size="sm">
                      清除
                    </Button>
                  </div>

                  <div className="space-y-3">
                    <div className="flex items-center justify-between">
                      <Label>自动清理缓存</Label>
                      <span className="text-sm text-muted-foreground">
                        超过 {aiSettings.cacheSize} GB 时自动清理
                      </span>
                    </div>
                    <Slider
                      value={[aiSettings.cacheSize]}
                      onValueChange={([value]) =>
                        setAiSettings({ ...aiSettings, cacheSize: value })
                      }
                      min={10}
                      max={100}
                      step={10}
                      className="w-full"
                    />
                  </div>
                </CardContent>
              </Card>

              <Card className="bg-card border-border">
                <CardHeader>
                  <CardTitle>订阅计划</CardTitle>
                  <CardDescription>您当前的订阅和配额信息</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="p-4 bg-primary/10 border border-primary/30 rounded-lg">
                    <div className="flex items-center justify-between mb-4">
                      <div className="flex items-center gap-3">
                        <CreditCard className="h-6 w-6 text-primary" />
                        <div>
                          <h4 className="font-semibold text-primary">Pro 专业版</h4>
                          <p className="text-sm text-muted-foreground">¥299/月</p>
                        </div>
                      </div>
                      <Button size="sm">升级计划</Button>
                    </div>
                    <div className="grid grid-cols-3 gap-4 text-sm">
                      <div className="flex items-center gap-2">
                        <CheckCircle2 className="h-4 w-4 text-success" />
                        <span>500 GB 存储空间</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <CheckCircle2 className="h-4 w-4 text-success" />
                        <span>无限 AI 生成</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <CheckCircle2 className="h-4 w-4 text-success" />
                        <span>优先渲染队列</span>
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </TabsContent>
          </Tabs>

          {/* Save Actions */}
          <div className="flex items-center justify-between mt-8 pt-6 border-t border-border">
            {saveMessage && (
              <span className={`text-sm ${saveMessage.type === "success" ? "text-green-500" : "text-destructive"}`}>
                {saveMessage.text}
              </span>
            )}
            {!saveMessage && <span />}
            <div className="flex items-center gap-3">
              <Button variant="outline" className="gap-2" onClick={handleReset} disabled={saving}>
                <RotateCcw className="h-4 w-4" />
                重置更改
              </Button>
              <Button
                className="gap-2 bg-primary text-primary-foreground hover:bg-primary/90"
                onClick={handleSave}
                disabled={saving}
              >
                {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}
                {saving ? "保存中..." : "保存设置"}
              </Button>
            </div>
          </div>
        </div>
      </div>
    </AppLayout>
  );
}
