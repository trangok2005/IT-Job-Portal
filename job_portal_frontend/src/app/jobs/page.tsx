import { getJobs, ApiError } from "@/lib/api-client";
import Link from "next/link";
import { JobCard } from "@/features/jobs/components/job-card";
import { SearchBar } from "@/features/jobs/components/search-bar";
import { Badge } from "@/components/ui/badge";
import {
  EXPERIENCE_LABELS,
  JOB_TYPE_LABELS,
  LOCATION_OPTIONS,
  WORKPLACE_TYPE_LABELS,
  isExperienceLevel,
  isJobType,
  isLocation,
  isWorkplaceType,
  formatVnd,
} from "@/features/jobs/utils";
import { JobFilters } from "@/features/jobs/components/job-filters";

export const metadata = { title: "Tìm việc làm IT | IT Job Portal" };

function toParam(value: string | string[] | undefined) {
  return Array.isArray(value) ? value[0] : value;
}

export default async function JobsPage({
  searchParams,
}: PageProps<"/jobs">) {
  const params = await searchParams;
  const keyword = toParam(params.keyword);
  const rawLocation = toParam(params.location);
  const location = isLocation(rawLocation) ? rawLocation : undefined;
  const rawWorkplaceType = toParam(params.workplace_type);
  const workplaceType = isWorkplaceType(rawWorkplaceType) ? rawWorkplaceType : undefined;
  const rawJobType = toParam(params.job_type);
  const rawExperienceLevel = toParam(params.experience_level);
  const jobType = isJobType(rawJobType) ? rawJobType : undefined;
  const experienceLevel = isExperienceLevel(rawExperienceLevel)
    ? rawExperienceLevel
    : undefined;
  const rawSalaryMin = toParam(params.salary_min);
  const parsedSalaryMin = rawSalaryMin === undefined ? undefined : Number(rawSalaryMin);
  const salaryMin = parsedSalaryMin !== undefined && Number.isInteger(parsedSalaryMin) && parsedSalaryMin >= 0
    ? parsedSalaryMin
    : undefined;
  const rawPage = Number(toParam(params.page));
  const page = Number.isInteger(rawPage) && rawPage > 0 ? rawPage : 1;

  let jobsResult;
  let throttled = false;
  try {
    jobsResult = await getJobs({
      keyword,
      workplace_type: workplaceType,
      location,
      job_type: jobType,
      experience_level: experienceLevel,
      salary_min: salaryMin,
      page,
    });
  } catch (error) {
    if (error instanceof ApiError && error.status === 429) {
      throttled = true;
      jobsResult = { results: [], count: 0, next: null, previous: null };
    } else {
      throw error;
    }
  }

  const jobs = jobsResult.results;
  const count = jobsResult.count;
  const searchFallback = jobsResult.search_fallback === true;

  const filterChips = [
    keyword ? { key: "keyword", label: keyword } : null,
    workplaceType ? { key: "workplace_type", label: WORKPLACE_TYPE_LABELS[workplaceType] } : null,
    location ? { key: "location", label: LOCATION_OPTIONS.find((option) => option.value === location)?.label ?? location } : null,
    jobType ? { key: "job_type", label: JOB_TYPE_LABELS[jobType] ?? jobType } : null,
    experienceLevel
      ? { key: "experience_level", label: EXPERIENCE_LABELS[experienceLevel] ?? experienceLevel }
      : null,
    salaryMin !== undefined ? { key: "salary_min", label: `Lương từ ${formatVnd(salaryMin)}` } : null,
  ].filter((c): c is { key: string; label: string } => c !== null);

  const activeParams = new URLSearchParams();
  if (keyword) activeParams.set("keyword", keyword);
  if (workplaceType) activeParams.set("workplace_type", workplaceType);
  if (location) activeParams.set("location", location);
  if (jobType) activeParams.set("job_type", jobType);
  if (experienceLevel) activeParams.set("experience_level", experienceLevel);
  if (salaryMin !== undefined) activeParams.set("salary_min", String(salaryMin));
  const hrefWithout = (key: string) => {
    const next = new URLSearchParams(activeParams);
    next.delete(key);
    return `/jobs${next.size ? `?${next.toString()}` : ""}`;
  };
  const pageHref = (target: number) => {
    const next = new URLSearchParams(activeParams);
    if (target > 1) next.set("page", String(target));
    return `/jobs${next.size ? `?${next.toString()}` : ""}`;
  };
  const hasNextPage = Boolean(jobsResult.next);
  const hasPreviousPage = Boolean(jobsResult.previous);

  return (
    <div className="mx-auto w-full max-w-6xl px-4 py-10 sm:px-6">
      <h1 className="text-2xl font-bold text-zinc-900">Tìm việc làm</h1>
      <p className="mt-1 text-sm text-zinc-500">
        {count > 0 ? `${count.toLocaleString("vi-VN")} việc làm đang tuyển` : "Kết quả tìm kiếm"}
      </p>

      <div className="mt-6">
        <SearchBar key={keyword ?? ""} initialKeyword={keyword ?? ""} />
      </div>

      {/* Bộ lọc bổ sung (UC-03) */}
      <div className="mt-4">
        <JobFilters workplaceType={workplaceType} jobType={jobType} experienceLevel={experienceLevel} salaryMin={salaryMin} location={location} />
      </div>

      {filterChips.length > 0 && (
        <div className="mt-4 flex flex-wrap items-center gap-2">
          {filterChips.map((chip) => (
            <Badge key={chip.key} variant="outline" className="gap-1">
              {chip.label}
              <Link href={hrefWithout(chip.key)} className="ml-1 text-zinc-400 hover:text-zinc-600">
                ×
              </Link>
            </Badge>
          ))}
        </div>
      )}

      {searchFallback && (
        <div className="mt-4 rounded-xl border border-amber-300 bg-amber-50 px-4 py-3 text-sm text-amber-800">
          Hệ thống AI đang bận, kết quả được tìm bằng PostgreSQL Full-Text Search.
        </div>
      )}

      {throttled ? (
        <div className="mt-8 rounded-xl border border-amber-300 bg-amber-50 p-12 text-center text-sm font-medium text-amber-800">
          Bạn đang tìm kiếm quá nhanh. Vui lòng thử lại sau ít giây.
        </div>
      ) : jobs.length === 0 ? (
        <div className="mt-8 rounded-xl border border-dashed border-zinc-200 bg-zinc-50 p-12 text-center text-sm text-zinc-500">
          Không tìm thấy công việc phù hợp. Hãy thử từ khóa khác hoặc bỏ bớt bộ lọc.
        </div>
      ) : (
        <div className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {jobs.map((job, i) => (
            <JobCard key={job.id} job={job} index={i} showMatchScore={Boolean(keyword?.trim())} />
          ))}
        </div>
      )}
      {(hasPreviousPage || hasNextPage) && (
        <nav className="mt-8 flex items-center justify-center gap-3" aria-label="Phân trang">
          {hasPreviousPage && <Link href={pageHref(page - 1)} className="rounded-xl border border-zinc-200 px-4 py-2 text-sm font-medium hover:border-primary hover:text-primary">Trang trước</Link>}
          <span className="text-sm text-zinc-500">Trang {page}</span>
          {hasNextPage && <Link href={pageHref(page + 1)} className="rounded-xl border border-zinc-200 px-4 py-2 text-sm font-medium hover:border-primary hover:text-primary">Trang sau</Link>}
        </nav>
      )}
    </div>
  );
}
