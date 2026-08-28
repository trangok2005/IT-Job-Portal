"use client";

import { ArrowLeft, ArrowRight, RefreshCw, Sparkles, UserRoundPen } from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { getRecommendedJobs } from "@/features/jobs/api";
import { JobCard } from "@/features/jobs/components/job-card";
import type { RecommendedJobDto } from "@/lib/types";

const PAGE_SIZE = 20;

export function RecommendedJobs() {
  const [jobs, setJobs] = useState<RecommendedJobDto[]>([]);
  const [count, setCount] = useState(0);
  const [page, setPage] = useState(1);
  const [reloadKey, setReloadKey] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    getRecommendedJobs(page)
      .then((result) => {
        if (!active) return;
        setJobs(result.results);
        setCount(result.count);
      })
      .catch((reason: unknown) => {
        if (!active) return;
        setError(reason instanceof Error ? reason.message : "Không thể tải việc làm gợi ý.");
      })
      .finally(() => {
        if (active) setLoading(false);
      });

    return () => {
      active = false;
    };
  }, [page, reloadKey]);

  const pageCount = Math.ceil(count / PAGE_SIZE);
  const hasScores = jobs.some((job) => job.match_score !== null);
  const reload = () => {
    setLoading(true);
    setError(null);
    setReloadKey((key) => key + 1);
  };
  const goToPage = (nextPage: number) => {
    setLoading(true);
    setError(null);
    setPage(nextPage);
  };

  return (
    <div className="mx-auto w-full max-w-6xl px-4 py-8 sm:px-6 sm:py-10">
      <section className="overflow-hidden rounded-3xl bg-zinc-950 px-6 py-8 text-white sm:px-9 sm:py-10">
        <div className="max-w-3xl">
          <span className="inline-flex items-center gap-2 rounded-full bg-white/10 px-3 py-1 text-xs font-medium text-emerald-300">
            <Sparkles className="size-3.5" /> Gợi ý từ hồ sơ của bạn
          </span>
          <h1 className="mt-4 text-3xl font-bold tracking-tight sm:text-4xl">Việc làm phù hợp</h1>
          <p className="mt-3 max-w-2xl text-sm leading-6 text-zinc-300 sm:text-base">
            Mức độ phù hợp kết hợp nội dung ngữ nghĩa, kỹ năng, kinh nghiệm và học vấn để ưu tiên những công việc gần nhất với hồ sơ của bạn.
          </p>
          <div className="mt-6 flex flex-wrap gap-3">
            <Button asChild variant="accent">
              <Link href="/jobs">Tìm kiếm theo từ khóa</Link>
            </Button>
            <Button asChild variant="outline" className="border-white/25 bg-transparent text-white hover:bg-white/10 hover:text-white">
              <Link href="/candidate/profile"><UserRoundPen /> Cập nhật hồ sơ</Link>
            </Button>
          </div>
        </div>
      </section>

      <div className="mt-8 flex flex-col justify-between gap-3 sm:flex-row sm:items-end">
        <div>
          <h2 className="text-xl font-bold text-zinc-900">Dành cho bạn</h2>
          <p className="mt-1 text-sm text-zinc-500">
            {count > 0 ? `${count.toLocaleString("vi-VN")} việc làm đang tuyển được xếp theo mức độ phù hợp.` : "Kết quả được cập nhật theo phiên bản hồ sơ mới nhất."}
          </p>
        </div>
        <Button variant="outline" size="sm" onClick={reload} disabled={loading}>
          <RefreshCw className={loading ? "animate-spin" : ""} /> Làm mới
        </Button>
      </div>

      {!loading && jobs.length > 0 && !hasScores && (
        <div className="mt-5 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
          AI đang đồng bộ hồ sơ hoặc tin tuyển dụng. Danh sách tạm thời hiển thị việc mới nhất; hãy làm mới sau ít phút để xem điểm phù hợp.
        </div>
      )}

      {error && (
        <div className="mt-6 rounded-xl border border-red-200 bg-red-50 p-5 text-sm text-red-700">
          <p>{error}</p>
          <Button variant="outline" size="sm" className="mt-3" onClick={reload}>Thử lại</Button>
        </div>
      )}

      {loading ? (
        <div className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 6 }, (_, index) => <div key={index} className="h-52 animate-pulse rounded-xl bg-zinc-100" />)}
        </div>
      ) : !error && jobs.length === 0 ? (
        <div className="mt-6 rounded-xl border border-dashed border-zinc-200 bg-zinc-50 p-12 text-center">
          <Sparkles className="mx-auto size-9 text-zinc-300" />
          <p className="mt-3 font-medium text-zinc-700">Chưa có việc làm phù hợp để gợi ý.</p>
          <p className="mt-1 text-sm text-zinc-500">Hãy hoàn thiện hồ sơ hoặc xem toàn bộ công việc đang tuyển.</p>
          <Button asChild className="mt-5"><Link href="/jobs">Khám phá việc làm</Link></Button>
        </div>
      ) : !error ? (
        <div className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {jobs.map((job, index) => <JobCard key={job.id} job={job} index={index} showMatchScore />)}
        </div>
      ) : null}

      {!loading && !error && pageCount > 1 && (
        <nav className="mt-8 flex items-center justify-center gap-3" aria-label="Phân trang việc làm gợi ý">
          <Button variant="outline" disabled={page === 1} onClick={() => goToPage(page - 1)}>
            <ArrowLeft /> Trang trước
          </Button>
          <span className="text-sm text-zinc-500">Trang {page} / {pageCount}</span>
          <Button variant="outline" disabled={page === pageCount} onClick={() => goToPage(page + 1)}>
            Trang sau <ArrowRight />
          </Button>
        </nav>
      )}
    </div>
  );
}
