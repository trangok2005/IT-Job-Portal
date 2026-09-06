import { Suspense } from "react";

import { SkillsAdmin } from "@/features/admin/components/skills-admin";

export const metadata = { title: "Quản lý kỹ năng | IT Job Portal" };

export default function AdminSkillsPage() {
  return (
    <Suspense fallback={<div className="mx-auto min-h-96 w-full max-w-7xl animate-pulse px-4 py-10 text-sm text-zinc-500 sm:px-6">Đang tải dữ liệu quản trị...</div>}>
      <SkillsAdmin />
    </Suspense>
  );
}
