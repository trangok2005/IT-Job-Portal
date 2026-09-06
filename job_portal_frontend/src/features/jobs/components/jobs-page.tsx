"use client";

import { Loader2, Sparkles } from "lucide-react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useState, useSyncExternalStore } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { getRecommendedJobs } from "@/features/jobs/api";
import { JobCard } from "@/features/jobs/components/job-card";
import { JobFilters } from "@/features/jobs/components/job-filters";
import { SearchBar } from "@/features/jobs/components/search-bar";
import {
  EXPERIENCE_LABELS,
  formatVnd,
  isExperienceLevel,
  isJobType,
  isLocation,
  isWorkplaceType,
  JOB_TYPE_LABELS,
  LOCATION_OPTIONS,
  WORKPLACE_TYPE_LABELS,
} from "@/features/jobs/utils";
import { ApiError, getJobs } from "@/lib/api-client";
import { useAuth } from "@/lib/auth-provider";
import type { JobDto } from "@/lib/types";
import { cn } from "@/lib/utils";

type JobsTab = "all" | "recommended";

const MIN_RECOMMENDED_MATCH_SCORE = 50;

type JobsResultState = {
  requestKey: string;
  jobs: JobDto[];
  count: number;
  hasNextPage: boolean;
  hasPreviousPage: boolean;
  loading: boolean;
  error: string | null;
  searchFallback: boolean;
};

const INITIAL_RESULT: JobsResultState = {
  requestKey: "",
  jobs: [],
  count: 0,
  hasNextPage: false,
  hasPreviousPage: false,
  loading: true,
  error: null,
  searchFallback: false,
};

const subscribeHydration = () => () => {};
const getClientSnapshot = () => true;
const getServerSnapshot = () => false;

function jobsHref(params: URLSearchParams) {
  return `/jobs${params.size ? `?${params.toString()}` : ""}`;
}

export function JobsPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { user } = useAuth();
  const authReady = useSyncExternalStore(subscribeHydration, getClientSnapshot, getServerSnapshot);
  const queryString = searchParams.toString();
  const rawTab = searchParams.get("tab");
  const activeTab: JobsTab = rawTab === "recommended" ? "recommended" : "all";
  const keyword = searchParams.get("keyword") || undefined;
  const rawLocation = searchParams.get("location") || undefined;
  const location = isLocation(rawLocation) ? rawLocation : undefined;
  const rawWorkplaceType = searchParams.get("workplace_type") || undefined;
  const workplaceType = isWorkplaceType(rawWorkplaceType) ? rawWorkplaceType : undefined;
  const rawJobType = searchParams.get("job_type") || undefined;
  const jobType = isJobType(rawJobType) ? rawJobType : undefined;
  const rawExperienceLevel = searchParams.get("experience_level") || undefined;
  const experienceLevel = isExperienceLevel(rawExperienceLevel) ? rawExperienceLevel : undefined;
  const parsedSalaryMin = Number(searchParams.get("salary_min"));
  const salaryMin = Number.isInteger(parsedSalaryMin) && parsedSalaryMin >= 0
    && searchParams.has("salary_min") ? parsedSalaryMin : undefined;
  const parsedPage = Number(searchParams.get("page"));
  const page = Number.isInteger(parsedPage) && parsedPage > 0 ? parsedPage : 1;
  const recommendationAccess = activeTab === "all" ? "public"
    : !authReady ? "waiting"
    : !user ? "guest"
    : user.role === "CANDIDATE" ? "candidate" : "blocked";
  const [result, setResult] = useState<JobsResultState>(INITIAL_RESULT);
  const [reloadKey, setReloadKey] = useState(0);
  const requestKey = `${queryString}|${recommendationAccess}|${reloadKey}`;
  const loading = result.loading || result.requestKey !== requestKey;

  useEffect(() => {
    if (rawTab !== null && rawTab !== "all" && rawTab !== "recommended") {
      const next = new URLSearchParams(queryString);
      next.set("tab", "all");
      next.delete("page");
      router.replace(jobsHref(next));
      return;
    }

    if (activeTab === "recommended") {
      if (recommendationAccess === "waiting") return;
      if (recommendationAccess === "guest") {
        router.replace("/login?next=%2Fjobs%3Ftab%3Drecommended");
        return;
      }
      if (recommendationAccess === "blocked") {
        const next = new URLSearchParams(queryString);
        next.set("tab", "all");
        next.delete("page");
        router.replace(jobsHref(next));
        return;
      }
    }

    const controller = new AbortController();

    const request = activeTab === "recommended"
      ? getRecommendedJobs(controller.signal).then((jobsResult) => {
          const jobs = jobsResult.results.filter(
            (job) => job.match_score !== null && job.match_score > MIN_RECOMMENDED_MATCH_SCORE,
          );
          return {
            jobsResult: {
              ...jobsResult,
              results: jobs,
              count: jobs.length,
              next: null,
              previous: null,
            },
            searchFallback: false,
          };
        })
      : getJobs({
          keyword,
          workplace_type: workplaceType,
          location,
          job_type: jobType,
          experience_level: experienceLevel,
          salary_min: salaryMin,
          page,
        }, controller.signal).then((jobsResult) => ({
          jobsResult,
          searchFallback: jobsResult.search_fallback === true,
        }));

    request
      .then(({ jobsResult, searchFallback }) => {
        const jobs: JobDto[] = jobsResult.results;
        setResult({
          requestKey,
          jobs,
          count: jobsResult.count,
          hasNextPage: Boolean(jobsResult.next),
          hasPreviousPage: Boolean(jobsResult.previous),
          loading: false,
          error: null,
          searchFallback,
        });
      })
      .catch((reason: unknown) => {
        if (controller.signal.aborted) return;
        if (activeTab === "recommended" && reason instanceof ApiError && reason.status === 401) {
          router.replace("/login?next=%2Fjobs%3Ftab%3Drecommended");
          return;
        }
        const message = reason instanceof ApiError && reason.status === 429
          ? "Bạn đang thao tác quá nhanh. Vui lòng thử lại sau ít giây."
          : reason instanceof Error ? reason.message : "Không thể tải danh sách việc làm.";
        setResult({ ...INITIAL_RESULT, requestKey, loading: false, error: message });
      });

    return () => controller.abort();
  }, [activeTab, experienceLevel, jobType, keyword, location, page, queryString, rawTab, recommendationAccess, reloadKey, requestKey, router, salaryMin, workplaceType]);

  const showRecommendedTab = !authReady || !user || user.role === "CANDIDATE";
  const tabHref = (tab: JobsTab) => {
    const next = new URLSearchParams(queryString);
    next.set("tab", tab);
    next.delete("page");
    return jobsHref(next);
  };
  const pageHref = (target: number) => {
    const next = new URLSearchParams(queryString);
    if (target > 1) next.set("page", String(target));
    else next.delete("page");
    return jobsHref(next);
  };
  const hrefWithout = (key: string) => {
    const next = new URLSearchParams(queryString);
    next.delete(key);
    next.set("tab", "all");
    next.delete("page");
    return jobsHref(next);
  };
  const filterChips = [
    keyword ? { key: "keyword", label: keyword } : null,
    workplaceType ? { key: "workplace_type", label: WORKPLACE_TYPE_LABELS[workplaceType] } : null,
    location ? { key: "location", label: LOCATION_OPTIONS.find((option) => option.value === location)?.label ?? location } : null,
    jobType ? { key: "job_type", label: JOB_TYPE_LABELS[jobType] } : null,
    experienceLevel ? { key: "experience_level", label: EXPERIENCE_LABELS[experienceLevel] } : null,
    salaryMin !== undefined ? { key: "salary_min", label: `Lương từ ${formatVnd(salaryMin)}` } : null,
  ].filter((chip): chip is { key: string; label: string } => chip !== null);

  return (
    <div className="mx-auto w-full max-w-7xl px-4 py-8 sm:px-6 sm:py-10">
      <h1 className="text-2xl font-bold text-zinc-900">Tìm việc làm</h1>
      <p className="mt-1 text-sm text-zinc-500">
        {loading ? "Đang cập nhật danh sách việc làm..." : `${result.count.toLocaleString("vi-VN")} việc làm đang tuyển`}
      </p>

      <div className="mt-6"><SearchBar key={keyword ?? ""} initialKeyword={keyword ?? ""} /></div>
      <div className="mt-4">
        <JobFilters workplaceType={workplaceType} jobType={jobType} experienceLevel={experienceLevel} salaryMin={salaryMin} location={location} />
      </div>
      {activeTab === "recommended" && (
        <p className="mt-2 text-xs text-zinc-500">Tìm kiếm hoặc thay đổi bộ lọc sẽ chuyển sang tab Tất cả việc làm.</p>
      )}

      {filterChips.length > 0 && (
        <div className="mt-4 flex flex-wrap items-center gap-2">
          {filterChips.map((chip) => (
            <Badge key={chip.key} variant="outline" className="gap-1">
              {chip.label}
              <Link href={hrefWithout(chip.key)} className="ml-1 text-zinc-400 hover:text-zinc-600">×</Link>
            </Badge>
          ))}
        </div>
      )}

      <div className="mt-6 flex border-b border-zinc-200" role="tablist" aria-label="Loại danh sách việc làm">
        <Link
          href={tabHref("all")}
          role="tab"
          aria-selected={activeTab === "all"}
          className={cn("border-b-2 px-4 py-3 text-sm font-semibold", activeTab === "all" ? "border-primary text-primary" : "border-transparent text-zinc-500 hover:text-zinc-800")}
        >
          Tất cả việc làm
        </Link>
        {showRecommendedTab && (
          <Link
            href={tabHref("recommended")}
            role="tab"
            aria-selected={activeTab === "recommended"}
            onClick={(event) => {
              if (authReady && !user) {
                event.preventDefault();
                router.push("/login?next=%2Fjobs%3Ftab%3Drecommended");
              }
            }}
            className={cn("border-b-2 px-4 py-3 text-sm font-semibold", activeTab === "recommended" ? "border-primary text-primary" : "border-transparent text-zinc-500 hover:text-zinc-800")}
          >
            Gợi ý cho bạn
          </Link>
        )}
      </div>

      {result.searchFallback && (
        <div className="mt-4 rounded-xl border border-amber-300 bg-amber-50 px-4 py-3 text-sm text-amber-800">
          Hệ thống AI đang bận, kết quả được tìm bằng từ khóa cơ bản.
        </div>
      )}
      {loading ? (
        <div className="mt-8 flex min-h-72 items-center justify-center rounded-xl border border-zinc-200 bg-white text-sm text-zinc-500">
          <Loader2 className="mr-2 size-5 animate-spin" /> Đang tải việc làm...
        </div>
      ) : result.error ? (
        <div className="mt-8 rounded-xl border border-red-200 bg-red-50 p-8 text-center text-sm text-red-700">
          <p>{result.error}</p>
          <Button variant="outline" className="mt-4" onClick={() => setReloadKey((key) => key + 1)}>Thử lại</Button>
        </div>
      ) : result.jobs.length === 0 ? (
        <div className="mt-8 rounded-xl border border-dashed border-zinc-200 bg-zinc-50 p-12 text-center text-sm text-zinc-500">
          {activeTab === "recommended" ? (
            <><Sparkles className="mx-auto mb-3 size-8 text-zinc-300" />Không có việc làm phù hợp trên 50%.</>
          ) : "Không tìm thấy công việc phù hợp. Hãy thử từ khóa khác hoặc bỏ bớt bộ lọc."}
        </div>
      ) : (
        <div className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {result.jobs.map((job, index) => (
            <JobCard
              key={job.id}
              job={job}
              index={index}
              showMatchScore={activeTab === "recommended" || Boolean(keyword?.trim())}
            />
          ))}
        </div>
      )}

      {!loading && !result.error && (result.hasPreviousPage || result.hasNextPage) && (
        <nav className="mt-8 flex items-center justify-center gap-3" aria-label="Phân trang">
          {result.hasPreviousPage && <Link href={pageHref(page - 1)} className="rounded-xl border border-zinc-200 px-4 py-2 text-sm font-medium hover:border-primary hover:text-primary">Trang trước</Link>}
          <span className="text-sm text-zinc-500">Trang {page}</span>
          {result.hasNextPage && <Link href={pageHref(page + 1)} className="rounded-xl border border-zinc-200 px-4 py-2 text-sm font-medium hover:border-primary hover:text-primary">Trang sau</Link>}
        </nav>
      )}
    </div>
  );
}
