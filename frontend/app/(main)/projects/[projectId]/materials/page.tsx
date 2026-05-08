import { redirect } from 'next/navigation';

// 重构后 characters / locations 已删，materials 索引直接跳到 assets 子页。
export default async function MaterialsPage({
  params,
}: {
  params: Promise<{ projectId: string }>;
}) {
  const { projectId } = await params;
  redirect(`/projects/${projectId}/materials/assets`);
}
