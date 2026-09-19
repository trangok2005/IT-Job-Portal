import { ArrowLeft } from "lucide-react";
import Link from "next/link";
import { notFound } from "next/navigation";

import { JobDetail } from "@/features/jobs/components/job-detail";
import { ApiError, getJob } from "@/lib/api-client";

export const metadata = { title: "Chi tiết việc làm | IT Job Portal" };

export default async function JobDetailPage({ params }: PageProps<"/jobs/[jobId]">) {
  const { jobId } = await params;
  let job;
  try {
    job = await getJob(jobId);
  } catch (error) {
    if (!(error instanceof ApiError) || error.status !== 404) throw error;
    job = null;
  }

  if (!job) notFound();

  return (
    <div className="bg-slate-50">
      <div className="mx-auto w-full max-w-[1200px] px-4 py-5 md:px-6 md:py-8">
        <Link
          href="/jobs"
          className="mb-5 inline-flex min-h-11 items-center gap-2 rounded-lg pr-3 text-sm font-medium text-slate-500 transition-colors hover:text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 focus-visible:ring-offset-slate-50 md:mb-6"
        >
          <ArrowLeft className="size-4" aria-hidden="true" />
          Quay lại danh sách việc làm
        </Link>

        <JobDetail job={job} headingLevel="h1" />
      </div>
    </div>
  );
}
