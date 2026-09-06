import { Suspense } from "react";

import { JobsPage as JobsBrowser } from "@/features/jobs/components/jobs-page";

export const metadata = { title: "Tìm việc làm IT | IT Job Portal" };

export default function JobsPage() {
  return (
    <Suspense fallback={<div className="mx-auto min-h-96 w-full max-w-7xl animate-pulse px-4 py-10 text-sm text-zinc-500 sm:px-6">Đang tải việc làm...</div>}>
      <JobsBrowser />
    </Suspense>
  );
}
