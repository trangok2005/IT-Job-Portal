import { ArrowLeft, MapPin, TrendingUp } from "lucide-react";
import Link from "next/link";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { getJob } from "@/lib/api-client";
import { EXPERIENCE_LABELS, formatSalary, JOB_TYPE_LABELS, WORKPLACE_TYPE_LABELS } from "@/features/jobs/utils";
import { ApplyButton } from "@/features/applications/components/apply-button";

export const metadata = { title: "Chi tiết việc làm | IT Job Portal" };

export default async function JobDetailPage({ params }: PageProps<"/jobs/[jobId]">) {
  const { jobId } = await params;
  const job = await getJob(jobId).catch(() => null);

  if (!job) {
    return (
      <div className="mx-auto w-full max-w-3xl px-4 py-20 text-center sm:px-6">
        <h1 className="text-xl font-bold text-zinc-900">Không tìm thấy việc làm</h1>
        <p className="mt-2 text-sm text-zinc-500">Tin tuyển dụng không tồn tại hoặc đã bị đóng.</p>
        <Button asChild className="mt-6">
          <Link href="/jobs">
            <ArrowLeft className="h-4 w-4" /> Quay lại tìm việc
          </Link>
        </Button>
      </div>
    );
  }

  return (
    <div className="mx-auto w-full max-w-4xl px-4 py-10 sm:px-6">
      <Button asChild variant="ghost" size="sm" className="mb-6 -ml-3">
        <Link href="/jobs">
          <ArrowLeft className="h-4 w-4" /> Tìm việc làm
        </Link>
      </Button>

      <div className="rounded-xl border border-zinc-200 bg-white p-6 shadow-sm sm:p-8">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-start">
          <span className="flex h-14 w-14 shrink-0 items-center justify-center rounded-xl bg-primary text-xl font-bold text-white">
            {job.company_name.charAt(0).toUpperCase()}
          </span>
          <div className="flex-1">
            <h1 className="text-2xl font-bold text-zinc-900">{job.title}</h1>
            <p className="mt-1 text-sm text-zinc-500">{job.company_name}</p>
            <div className="mt-3 flex flex-wrap items-center gap-2">
              <Badge variant="default">{JOB_TYPE_LABELS[job.job_type] ?? job.job_type}</Badge>
              <Badge variant="outline">{WORKPLACE_TYPE_LABELS[job.workplace_type]}</Badge>
              {job.experience_level && (
                <Badge variant="outline">
                  {EXPERIENCE_LABELS[job.experience_level] ?? job.experience_level}
                </Badge>
              )}
              {job.skills.map((skill) => (
                <Badge key={skill.id} variant="outline">
                  {skill.skill_name}
                </Badge>
              ))}
            </div>
            <div className="mt-5"><ApplyButton jobId={job.id} /></div>
          </div>
        </div>

        <div className="mt-6 grid gap-3 rounded-xl bg-zinc-50 p-4 text-sm sm:grid-cols-2">
          <span className="inline-flex items-center gap-2 font-medium text-accent-600">
            <TrendingUp className="h-4 w-4" /> {formatSalary(job)}
          </span>
          <span className="inline-flex items-center gap-2 text-zinc-600">
            <MapPin className="h-4 w-4" /> {job.location || "—"}
          </span>
        </div>

        {job.description && (
          <section className="mt-8">
            <h2 className="text-lg font-semibold text-zinc-900">Mô tả công việc</h2>
            <p className="mt-3 whitespace-pre-line text-sm leading-relaxed text-zinc-600">
              {job.description}
            </p>
          </section>
        )}

        {job.requirements && (
          <section className="mt-8">
            <h2 className="text-lg font-semibold text-zinc-900">Yêu cầu</h2>
            <p className="mt-3 whitespace-pre-line text-sm leading-relaxed text-zinc-600">
              {job.requirements}
            </p>
          </section>
        )}

        {job.benefits && (
          <section className="mt-8">
            <h2 className="text-lg font-semibold text-zinc-900">Phúc lợi</h2>
            <p className="mt-3 whitespace-pre-line text-sm leading-relaxed text-zinc-600">
              {job.benefits}
            </p>
          </section>
        )}
      </div>
    </div>
  );
}
