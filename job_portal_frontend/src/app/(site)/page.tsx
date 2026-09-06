import { ArrowRight, Building2, Sparkles } from "lucide-react";
import Link from "next/link";

import { Button } from "@/components/ui/button";
import { getJobs } from "@/lib/api-client";
import { JobCard } from "@/features/jobs/components/job-card";
import { SearchBar } from "@/features/jobs/components/search-bar";
import type { JobDto } from "@/lib/types";

const HOT_SKILL_LIMIT = 6;

function topSkills(jobs: JobDto[], limit = HOT_SKILL_LIMIT): string[] {
  const counts = new Map<string, number>();
  for (const job of jobs) {
    for (const skill of job.skills) {
      counts.set(skill.skill_name, (counts.get(skill.skill_name) ?? 0) + 1);
    }
  }
  return [...counts.entries()]
    .sort((a, b) => b[1] - a[1])
    .slice(0, limit)
    .map(([name]) => name);
}

export default async function HomePage() {
  const jobsResult = await getJobs({ page_size: 8 }).catch(() => null);
  const jobCount = jobsResult?.count ?? 0;
  const jobs = jobsResult?.results ?? [];
  const hotSkills = topSkills(jobs);

  return (
    <div>
      <section className="bg-gradient-to-b from-primary-50 to-white">
        <div className="mx-auto flex w-full max-w-6xl flex-col items-center px-4 pb-16 pt-16 text-center sm:px-6 sm:pt-20">
          <span className="inline-flex items-center gap-2 rounded-full border border-primary-100 bg-white px-4 py-1.5 text-xs font-medium text-primary-700 shadow-sm">
            <Sparkles className="h-3.5 w-3.5" />
            Ghép nối CV và tin tuyển dụng theo mức độ phù hợp
          </span>
          <h1 className="mt-5 text-3xl font-extrabold tracking-tight text-zinc-900 sm:text-5xl">
            {jobCount > 0 ? (
              <>
                {jobCount.toLocaleString("vi-VN")}{" "}
                <span className="text-accent">việc làm IT</span> đang tuyển
              </>
            ) : (
              <>
                Tìm việc làm <span className="text-accent">IT</span> phù hợp với bạn
              </>
            )}
          </h1>
          <p className="mt-4 max-w-xl text-sm text-zinc-500 sm:text-base">
            Kết nối ứng viên IT với các công ty công nghệ hàng đầu. Đăng ký nhận gợi ý việc làm
            phù hợp dựa trên kỹ năng và kinh nghiệm của bạn.
          </p>

          <div className="mt-8 w-full max-w-3xl">
            <SearchBar />
          </div>

          {hotSkills.length > 0 && (
            <div className="mt-6 flex flex-wrap items-center justify-center gap-2">
              <span className="text-sm font-medium text-zinc-500">Đang tìm nhiều:</span>
              {hotSkills.map((skill) => (
                <Link
                  key={skill}
                  href={`/jobs?keyword=${encodeURIComponent(skill)}`}
                  className="rounded-full border border-zinc-200 bg-white px-3.5 py-1.5 text-sm text-zinc-600 transition-colors hover:border-primary-200 hover:bg-primary-50 hover:text-primary-700"
                >
                  {skill}
                </Link>
              ))}
            </div>
          )}
        </div>
      </section>

      <section className="bg-primary text-white">
        <div className="mx-auto flex w-full max-w-6xl flex-col items-center justify-between gap-6 px-4 py-10 sm:px-6 md:flex-row">
          <div className="flex items-center gap-4 text-center md:text-left">
            <span className="hidden h-12 w-12 items-center justify-center rounded-xl bg-white/10 md:flex">
              <Building2 className="h-6 w-6" />
            </span>
            <div>
              <h2 className="text-xl font-bold">Tuyển dụng IT nhanh chóng, hiệu quả</h2>
              <p className="mt-1 text-sm text-primary-100">
                Đăng tin tuyển dụng và tiếp cận ứng viên theo mức độ phù hợp.
              </p>
            </div>
          </div>
          <Button asChild variant="accent" size="lg" className="shrink-0">
            <Link href="/login?redirect_to=%2Femployer">
              Đăng nhập nhà tuyển dụng <ArrowRight className="h-4 w-4" />
            </Link>
          </Button>
        </div>
      </section>

      <section className="mx-auto w-full max-w-6xl px-4 py-14 sm:px-6">
        <div className="flex items-end justify-between gap-4">
          <div>
            <h2 className="text-2xl font-bold text-zinc-900">Việc làm mới nhất</h2>
            <p className="mt-1 text-sm text-zinc-500">
              Các vị trí đang tuyển gần đây, cập nhật liên tục.
            </p>
          </div>
          <Button asChild variant="outline" size="sm">
            <Link href="/jobs">
              Xem tất cả việc làm <ArrowRight className="h-4 w-4" />
            </Link>
          </Button>
        </div>

        {jobs.length === 0 ? (
          <div className="mt-8 rounded-xl border border-dashed border-zinc-200 bg-zinc-50 p-10 text-center text-sm text-zinc-500">
            Chưa có việc làm nào đang tuyển. Vui lòng quay lại sau.
          </div>
        ) : (
          <div className="mt-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {jobs.map((job, i) => (
              <JobCard key={job.id} job={job} index={i} />
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
