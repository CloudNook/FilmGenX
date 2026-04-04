'use client';

import { use, useState, useRef, useEffect } from 'react';
import { AppLayout } from '@/components/layout';
import {
  getProjectById,
  getConversationsByProjectId,
  getEpisodesByProjectId,
} from '@/lib/mock-data';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Separator } from '@/components/ui/separator';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import {
  Send,
  Plus,
  Paperclip,
  Image,
  FileText,
  Mic,
  MoreVertical,
  Sparkles,
  MessageSquare,
  Copy,
  Trash2,
  Edit,
  RefreshCw,
  ThumbsUp,
  ThumbsDown,
  ChevronRight,
  Film,
} from 'lucide-react';
import type { Message, Conversation } from '@/lib/types';

export default function ChatPage({
  params,
}: {
  params: Promise<{ projectId: string }>;
}) {
  const { projectId } = use(params);
  const project = getProjectById(projectId);
  const conversations = getConversationsByProjectId(projectId);
  const episodes = getEpisodesByProjectId(projectId);
  
  const [selectedConversation, setSelectedConversation] = useState<Conversation | null>(
    conversations[0] || null
  );
  const [messages, setMessages] = useState<Message[]>(
    selectedConversation?.messages || []
  );
  const [inputValue, setInputValue] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const [selectedEpisode, setSelectedEpisode] = useState<string>('all');
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  if (!project) {
    return (
      <AppLayout>
        <div className="flex items-center justify-center h-full">
          <p className="text-muted-foreground">项目不存在</p>
        </div>
      </AppLayout>
    );
  }

  const handleSendMessage = async () => {
    if (!inputValue.trim()) return;

    const userMessage: Message = {
      id: `msg-${Date.now()}`,
      role: 'user',
      content: inputValue,
      timestamp: new Date().toISOString(),
    };

    setMessages([...messages, userMessage]);
    setInputValue('');
    setIsTyping(true);

    // 模拟 AI 响应
    setTimeout(() => {
      const aiMessage: Message = {
        id: `msg-${Date.now() + 1}`,
        role: 'assistant',
        content: generateAIResponse(inputValue),
        timestamp: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, aiMessage]);
      setIsTyping(false);
    }, 1500);
  };

  const generateAIResponse = (input: string): string => {
    const responses = [
      `我理解您的需求。关于"${input.slice(0, 20)}..."的内容，我建议可以从以下几个方面来优化：\n\n1. **场景氛围**：增强视觉冲击力，使用更加戏剧性的光影效果\n2. **角色表现**：突出主角的内心冲突，通过微表情传达情感\n3. **节奏把控**：在关键时刻放慢节奏，给观众思考的空间\n\n需要我为您生成具体的分镜草图吗？`,
      `这是一个很好的想法！为了更好地实现这个效果，我们可以：\n\n- 使用**交叉剪辑**来增强紧张感\n- 配合**低沉的背景音乐**渲染氛围\n- 通过**特写镜头**展现角色的细腻情感\n\n您希望我先为哪个场景生成预览？`,
      `根据当前的剧情发展，我分析了几种可能的走向：\n\n**选项 A**：直接揭示真相，制造强烈的戏剧冲突\n**选项 B**：设置悬念，通过多个线索逐步引导观众\n**选项 C**：采用倒叙手法，从结局开始讲述\n\n每种方式都有其独特的叙事魅力，您更倾向于哪种风格？`,
    ];
    return responses[Math.floor(Math.random() * responses.length)];
  };

  const formatTime = (timestamp: string) => {
    const date = new Date(timestamp);
    return date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' });
  };

  const quickPrompts = [
    '优化这段对话的情感表达',
    '为这个场景生成分镜建议',
    '分析当前剧情的节奏',
    '创建新的角色设定',
  ];

  return (
    <AppLayout
      projectId={projectId}
      showSearch={false}
      breadcrumbs={[
        { label: '项目', href: '/projects' },
        { label: project.name, href: `/projects/${projectId}` },
        { label: 'AI 对话' },
      ]}
    >
      <div className="flex h-[calc(100vh-4rem)]">
        {/* Sidebar - Conversation List */}
        <div className="w-72 border-r border-border bg-card flex flex-col">
          <div className="p-4 border-b border-border">
            <Button className="w-full bg-primary text-primary-foreground hover:bg-primary/90">
              <Plus className="h-4 w-4 mr-2" />
              新建对话
            </Button>
          </div>

          <div className="p-4 border-b border-border">
            <Select value={selectedEpisode} onValueChange={setSelectedEpisode}>
              <SelectTrigger className="bg-secondary border-border">
                <SelectValue placeholder="筛选分集" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">全部分集</SelectItem>
                {episodes.map((ep) => (
                  <SelectItem key={ep.id} value={ep.id}>
                    第 {ep.number} 集 - {ep.title}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <ScrollArea className="flex-1">
            <div className="p-2 space-y-1">
              {conversations.map((conv) => (
                <button
                  key={conv.id}
                  onClick={() => {
                    setSelectedConversation(conv);
                    setMessages(conv.messages);
                  }}
                  className={`w-full text-left p-3 rounded-lg transition-colors ${
                    selectedConversation?.id === conv.id
                      ? 'bg-primary/10 border border-primary/30'
                      : 'hover:bg-secondary/50'
                  }`}
                >
                  <div className="flex items-center gap-2 mb-1">
                    <MessageSquare className="h-4 w-4 text-primary" />
                    <span className="font-medium text-foreground text-sm truncate">
                      {conv.title}
                    </span>
                  </div>
                  <p className="text-xs text-muted-foreground truncate">
                    {conv.messages[conv.messages.length - 1]?.content.slice(0, 50)}...
                  </p>
                  <p className="text-xs text-muted-foreground mt-1">
                    {formatTime(conv.updatedAt)}
                  </p>
                </button>
              ))}
            </div>
          </ScrollArea>
        </div>

        {/* Main Chat Area */}
        <div className="flex-1 flex flex-col bg-background">
          {/* Chat Header */}
          <div className="h-14 border-b border-border px-6 flex items-center justify-between bg-card">
            <div className="flex items-center gap-3">
              <div className="h-8 w-8 rounded-full bg-primary/10 flex items-center justify-center">
                <Sparkles className="h-4 w-4 text-primary" />
              </div>
              <div>
                <h2 className="font-medium text-foreground">
                  {selectedConversation?.title || 'FilmGenX AI 助手'}
                </h2>
                <p className="text-xs text-muted-foreground">
                  智能创作辅助
                </p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <Badge variant="outline" className="border-border">
                <Film className="h-3 w-3 mr-1" />
                第 3 集
              </Badge>
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button variant="ghost" size="icon">
                    <MoreVertical className="h-4 w-4" />
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end">
                  <DropdownMenuItem>
                    <Edit className="h-4 w-4 mr-2" />
                    重命名对话
                  </DropdownMenuItem>
                  <DropdownMenuItem>
                    <Copy className="h-4 w-4 mr-2" />
                    复制对话
                  </DropdownMenuItem>
                  <DropdownMenuItem className="text-destructive">
                    <Trash2 className="h-4 w-4 mr-2" />
                    删除对话
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            </div>
          </div>

          {/* Messages */}
          <ScrollArea className="flex-1 p-6">
            <div className="max-w-3xl mx-auto space-y-6">
              {/* Welcome Message */}
              {messages.length === 0 && (
                <div className="text-center py-12">
                  <div className="h-16 w-16 rounded-full bg-primary/10 flex items-center justify-center mx-auto mb-4">
                    <Sparkles className="h-8 w-8 text-primary" />
                  </div>
                  <h3 className="text-xl font-semibold text-foreground mb-2">
                    欢迎使用 FilmGenX AI 助手
                  </h3>
                  <p className="text-muted-foreground mb-6 max-w-md mx-auto">
                    我可以帮助您完成剧本创作、分镜设计、角色优化等多种创作任务
                  </p>
                  <div className="flex flex-wrap gap-2 justify-center">
                    {quickPrompts.map((prompt, index) => (
                      <Button
                        key={index}
                        variant="outline"
                        size="sm"
                        className="border-border hover:border-primary/50"
                        onClick={() => setInputValue(prompt)}
                      >
                        {prompt}
                      </Button>
                    ))}
                  </div>
                </div>
              )}

              {/* Message List */}
              {messages.map((message) => (
                <div
                  key={message.id}
                  className={`flex gap-4 ${
                    message.role === 'user' ? 'flex-row-reverse' : ''
                  }`}
                >
                  <Avatar className="h-8 w-8 shrink-0">
                    {message.role === 'user' ? (
                      <>
                        <AvatarImage src="/avatars/user-1.jpg" />
                        <AvatarFallback className="bg-primary text-primary-foreground">
                          张
                        </AvatarFallback>
                      </>
                    ) : (
                      <>
                        <AvatarFallback className="bg-primary/10 text-primary">
                          <Sparkles className="h-4 w-4" />
                        </AvatarFallback>
                      </>
                    )}
                  </Avatar>
                  <div
                    className={`flex-1 max-w-[80%] ${
                      message.role === 'user' ? 'text-right' : ''
                    }`}
                  >
                    <div
                      className={`inline-block rounded-2xl px-4 py-3 ${
                        message.role === 'user'
                          ? 'bg-primary text-primary-foreground rounded-tr-sm'
                          : 'bg-card border border-border rounded-tl-sm'
                      }`}
                    >
                      <p className="text-sm whitespace-pre-wrap leading-relaxed">
                        {message.content}
                      </p>
                    </div>
                    <div
                      className={`flex items-center gap-2 mt-1 ${
                        message.role === 'user' ? 'justify-end' : ''
                      }`}
                    >
                      <span className="text-xs text-muted-foreground">
                        {formatTime(message.timestamp)}
                      </span>
                      {message.role === 'assistant' && (
                        <div className="flex items-center gap-1">
                          <Button variant="ghost" size="icon" className="h-6 w-6">
                            <Copy className="h-3 w-3" />
                          </Button>
                          <Button variant="ghost" size="icon" className="h-6 w-6">
                            <RefreshCw className="h-3 w-3" />
                          </Button>
                          <Button variant="ghost" size="icon" className="h-6 w-6">
                            <ThumbsUp className="h-3 w-3" />
                          </Button>
                          <Button variant="ghost" size="icon" className="h-6 w-6">
                            <ThumbsDown className="h-3 w-3" />
                          </Button>
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              ))}

              {/* Typing Indicator */}
              {isTyping && (
                <div className="flex gap-4">
                  <Avatar className="h-8 w-8 shrink-0">
                    <AvatarFallback className="bg-primary/10 text-primary">
                      <Sparkles className="h-4 w-4" />
                    </AvatarFallback>
                  </Avatar>
                  <div className="flex items-center gap-1 bg-card border border-border rounded-2xl rounded-tl-sm px-4 py-3">
                    <div className="h-2 w-2 rounded-full bg-primary/60 animate-bounce" style={{ animationDelay: '0ms' }} />
                    <div className="h-2 w-2 rounded-full bg-primary/60 animate-bounce" style={{ animationDelay: '150ms' }} />
                    <div className="h-2 w-2 rounded-full bg-primary/60 animate-bounce" style={{ animationDelay: '300ms' }} />
                  </div>
                </div>
              )}

              <div ref={messagesEndRef} />
            </div>
          </ScrollArea>

          {/* Input Area */}
          <div className="border-t border-border p-4 bg-card">
            <div className="max-w-3xl mx-auto">
              <div className="flex items-end gap-3">
                <div className="flex-1 bg-secondary rounded-2xl border border-border focus-within:border-primary/50 transition-colors">
                  <div className="flex items-center gap-2 px-4 py-3">
                    <Input
                      value={inputValue}
                      onChange={(e) => setInputValue(e.target.value)}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter' && !e.shiftKey) {
                          e.preventDefault();
                          handleSendMessage();
                        }
                      }}
                      placeholder="输入您的创作需求..."
                      className="flex-1 border-0 bg-transparent focus-visible:ring-0 px-0"
                    />
                    <div className="flex items-center gap-1">
                      <Button variant="ghost" size="icon" className="h-8 w-8 text-muted-foreground hover:text-foreground">
                        <Paperclip className="h-4 w-4" />
                      </Button>
                      <Button variant="ghost" size="icon" className="h-8 w-8 text-muted-foreground hover:text-foreground">
                        <Image className="h-4 w-4" />
                      </Button>
                      <Button variant="ghost" size="icon" className="h-8 w-8 text-muted-foreground hover:text-foreground">
                        <Mic className="h-4 w-4" />
                      </Button>
                    </div>
                  </div>
                </div>
                <Button
                  onClick={handleSendMessage}
                  disabled={!inputValue.trim() || isTyping}
                  className="h-12 w-12 rounded-full bg-primary text-primary-foreground hover:bg-primary/90"
                >
                  <Send className="h-5 w-5" />
                </Button>
              </div>
              <p className="text-xs text-muted-foreground text-center mt-2">
                FilmGenX AI 可能会产生不准确的信息，请核实重要内容
              </p>
            </div>
          </div>
        </div>

        {/* Right Sidebar - Context Panel */}
        <div className="w-72 border-l border-border bg-card flex flex-col">
          <div className="p-4 border-b border-border">
            <h3 className="font-medium text-foreground">创作上下文</h3>
          </div>
          <ScrollArea className="flex-1 p-4">
            <div className="space-y-4">
              {/* Current Episode */}
              <Card className="bg-secondary border-border">
                <CardHeader className="p-3 pb-2">
                  <CardTitle className="text-sm">当前分集</CardTitle>
                </CardHeader>
                <CardContent className="p-3 pt-0">
                  <p className="text-sm font-medium text-foreground">第三集：第一次接触</p>
                  <p className="text-xs text-muted-foreground mt-1">
                    船员们在神秘行星上发现外星文明痕迹
                  </p>
                </CardContent>
              </Card>

              {/* Related Shots */}
              <div>
                <h4 className="text-sm font-medium text-foreground mb-2">相关镜头</h4>
                <div className="space-y-2">
                  {[1, 2, 3].map((num) => (
                    <div
                      key={num}
                      className="flex items-center gap-2 p-2 rounded-lg bg-secondary hover:bg-secondary/80 cursor-pointer transition-colors"
                    >
                      <div className="h-10 w-14 rounded bg-muted" />
                      <div className="flex-1 min-w-0">
                        <p className="text-xs font-medium text-foreground truncate">
                          镜头 {num}
                        </p>
                        <p className="text-xs text-muted-foreground">
                          {num * 2 + 3}秒
                        </p>
                      </div>
                      <ChevronRight className="h-4 w-4 text-muted-foreground" />
                    </div>
                  ))}
                </div>
              </div>

              {/* Quick Actions */}
              <div>
                <h4 className="text-sm font-medium text-foreground mb-2">快速操作</h4>
                <div className="space-y-2">
                  <Button variant="outline" size="sm" className="w-full justify-start border-border">
                    <FileText className="h-4 w-4 mr-2" />
                    生成剧本
                  </Button>
                  <Button variant="outline" size="sm" className="w-full justify-start border-border">
                    <Film className="h-4 w-4 mr-2" />
                    创建分镜
                  </Button>
                  <Button variant="outline" size="sm" className="w-full justify-start border-border">
                    <Sparkles className="h-4 w-4 mr-2" />
                    AI 润色
                  </Button>
                </div>
              </div>
            </div>
          </ScrollArea>
        </div>
      </div>
    </AppLayout>
  );
}
