import type { Metadata, Viewport } from 'next'
import { Inter, Noto_Sans_SC } from 'next/font/google'
import { Analytics } from '@vercel/analytics/next'
import { Providers } from '@/components/providers'
import './globals.css'

const inter = Inter({ 
  subsets: ["latin"],
  variable: '--font-inter'
});

const notoSansSC = Noto_Sans_SC({ 
  subsets: ["latin"],
  weight: ['400', '500', '600', '700'],
  variable: '--font-noto-sans-sc'
});

export const metadata: Metadata = {
  title: 'FilmGenX - AI 动画生产系统',
  description: '新一代 AI 驱动的动画内容生产系统，从剧本到成片的全流程智能化',
  generator: 'FilmGenX',
  icons: {
    icon: [
      {
        url: '/icon-light-32x32.png',
        media: '(prefers-color-scheme: light)',
      },
      {
        url: '/icon-dark-32x32.png',
        media: '(prefers-color-scheme: dark)',
      },
      {
        url: '/icon.svg',
        type: 'image/svg+xml',
      },
    ],
    apple: '/apple-icon.png',
  },
}

export const viewport: Viewport = {
  themeColor: '#ffffff',
  width: 'device-width',
  initialScale: 1,
}

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode
}>) {
  return (
    <html lang="zh-CN" suppressHydrationWarning>
      <body className={`${inter.variable} ${notoSansSC.variable} font-sans antialiased`}>
        <Providers>{children}</Providers>
        {process.env.NODE_ENV === 'production' && <Analytics />}
      </body>
    </html>
  )
}
