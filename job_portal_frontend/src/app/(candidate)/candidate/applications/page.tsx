import { Suspense } from "react";

import { CandidateApplications } from "@/features/applications/components/candidate-applications";

export const metadata = { title: "Đơn ứng tuyển của tôi | IT Job Portal" };

export default function CandidateApplicationsPage() {
  return (
    <Suspense fallback={<div className="mx-auto min-h-96 w-full max-w-6xl animate-pulse px-4 py-10 text-sm text-zinc-500 sm:px-6">Đang tải đơn ứng tuyển...</div>}>
      <CandidateApplications />
    </Suspense>
  );
}
