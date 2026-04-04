import { redirect } from 'next/navigation';

export default function HomePage() {
  // 默认重定向到项目列表
  redirect('/projects');
}
