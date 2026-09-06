import { ArrowLeft } from "lucide-react";
import Link from "next/link";
import { notFound } from "next/navigation";

import { Button } from "@/components/ui/button";
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
    <div className="mx-auto w-full max-w-4xl px-4 py-10 sm:px-6">
      <Button asChild variant="ghost" size="sm" className="mb-6 -ml-3">
        <Link href="/jobs">
          <ArrowLeft className="h-4 w-4" /> Tìm việc làm
        </Link>
      </Button>

      <JobDetail job={job} headingLevel="h1" />
    </div>
  );
}
