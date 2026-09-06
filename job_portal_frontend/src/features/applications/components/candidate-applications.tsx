"use client";

import { CalendarDays, FileText, RotateCcw } from "lucide-react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { getCandidateApplications } from "@/features/applications/api";
import {
  applicationStatusLabel,
  ApplicationStatusBadge,
  matchStatusLabel,
} from "@/features/applications/components/status-badge";
import type {
  ApplicationStatus,
  CandidateApplicationDto,
} from "@/features/applications/types";
import type { Paginated } from "@/lib/types";

const ORDERING_OPTIONS = [
  { value: "-created_at", label: "Mới nhất" },
  { value: "created_at", label: "Cũ nhất" },
  { value: "-match_score", label: "Điểm phù hợp cao nhất" },
  { value: "match_score", label: "Điểm phù hợp thấp nhất" },
] as const;

type ApplicationOrdering = (typeof ORDERING_OPTIONS)[number]["value"];

type ApplicationsState = {
  requestKey: string;
  result: Paginated<CandidateApplicationDto> | null;
  error: string | null;
};

const INITIAL_STATE: ApplicationsState = {
  requestKey: "",
  result: null,
  error: null,
};

function isApplicationStatus(value: string | null): value is ApplicationStatus {
  return value !== null && value in applicationStatusLabel;
}

function isApplicationOrdering(value: string | null): value is ApplicationOrdering {
  return ORDERING_OPTIONS.some((option) => option.value === value);
}

function formatApplicationDate(value: string) {
  return new Intl.DateTimeFormat("vi-VN", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
  }).format(new Date(value));
}

export function CandidateApplications() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const queryString = searchParams.toString();
  const status = isApplicationStatus(searchParams.get("status"))
    ? searchParams.get("status") as ApplicationStatus
    : "";
  const ordering = isApplicationOrdering(searchParams.get("ordering"))
    ? searchParams.get("ordering") as ApplicationOrdering
    : "-created_at";
  const rawPage = Number(searchParams.get("page"));
  const page = Number.isInteger(rawPage) && rawPage > 0 ? rawPage : 1;
  const [reloadKey, setReloadKey] = useState(0);
  const requestKey = `${status}|${ordering}|${page}|${reloadKey}`;
  const [state, setState] = useState<ApplicationsState>(INITIAL_STATE);
  const loading = state.requestKey !== requestKey;

  useEffect(() => {
    const controller = new AbortController();
    getCandidateApplications(page, status, ordering, controller.signal)
      .then((result) => {
        setState({ requestKey, result, error: null });
      })
      .catch((reason: unknown) => {
        if (controller.signal.aborted) return;
        setState({
          requestKey,
          result: null,
          error: reason instanceof Error
            ? reason.message
            : "Không thể tải danh sách đơn ứng tuyển.",
        });
      });
    return () => controller.abort();
  }, [ordering, page, requestKey, status]);

  const updateQuery = (changes: {
    status?: ApplicationStatus | "";
    ordering?: ApplicationOrdering;
    page?: number;
  }) => {
    const next = new URLSearchParams(queryString);
    const nextStatus = changes.status ?? status;
    const nextOrdering = changes.ordering ?? ordering;
    const nextPage = changes.page ?? page;

    if (nextStatus) next.set("status", nextStatus);
    else next.delete("status");
    if (nextOrdering !== "-created_at") next.set("ordering", nextOrdering);
    else next.delete("ordering");
    if (nextPage > 1) next.set("page", String(nextPage));
    else next.delete("page");
    router.push(`/candidate/applications${next.size ? `?${next}` : ""}`);
  };

  const clearFilters = () => router.push("/candidate/applications");
  const hasActiveFilters = Boolean(status) || ordering !== "-created_at" || page > 1;
  const result = state.result;
  const detailQuery = new URLSearchParams();
  if (status) detailQuery.set("status", status);
  if (ordering !== "-created_at") detailQuery.set("ordering", ordering);
  if (page > 1) detailQuery.set("page", String(page));
  const detailSuffix = detailQuery.size ? `?${detailQuery}` : "";

  return (
    <div className="mx-auto w-full max-w-6xl px-4 py-8 sm:px-6 sm:py-10 lg:px-8">
      <header>
        <h1 className="text-2xl font-bold tracking-tight text-zinc-900 sm:text-3xl">
          Đơn ứng tuyển của tôi
        </h1>
        <p className="mt-2 text-sm text-zinc-500 sm:text-base">
          Theo dõi tiến trình xử lý các công việc bạn đã ứng tuyển.
        </p>
      </header>

      <section className="mt-7" aria-label="Tổng quan đơn ứng tuyển">
        <div className="max-w-xs rounded-2xl border border-blue-100 bg-gradient-to-br from-white to-blue-50 p-5 shadow-sm">
          <p className="text-sm font-medium text-zinc-500">Tổng đơn</p>
          {loading ? (
            <div className="mt-3 h-9 w-20 animate-pulse rounded-lg bg-blue-100" />
          ) : (
            <p className="mt-2 text-3xl font-bold text-primary">{state.error ? "—" : result?.count ?? 0}</p>
          )}
          {status && <p className="mt-1 text-xs text-zinc-400">Trong trạng thái đang lọc</p>}
        </div>
      </section>

      <section className="mt-6 rounded-2xl border border-zinc-200 bg-white p-4 shadow-sm" aria-label="Bộ lọc đơn ứng tuyển">
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-[minmax(0,1fr)_minmax(0,1fr)_auto] lg:items-end">
          <label className="block text-sm font-medium text-zinc-700">
            Trạng thái
            <select
              value={status}
              onChange={(event) => updateQuery({
                status: event.target.value as ApplicationStatus | "",
                page: 1,
              })}
              className="mt-2 h-11 w-full rounded-xl border border-zinc-300 bg-white px-3.5 text-sm text-zinc-700 outline-none transition focus:border-primary focus:ring-2 focus:ring-primary-100"
            >
              <option value="">Tất cả trạng thái</option>
              {Object.entries(applicationStatusLabel).map(([value, label]) => (
                <option key={value} value={value}>{label}</option>
              ))}
            </select>
          </label>
          <label className="block text-sm font-medium text-zinc-700">
            Sắp xếp
            <select
              value={ordering}
              onChange={(event) => updateQuery({
                ordering: event.target.value as ApplicationOrdering,
                page: 1,
              })}
              className="mt-2 h-11 w-full rounded-xl border border-zinc-300 bg-white px-3.5 text-sm text-zinc-700 outline-none transition focus:border-primary focus:ring-2 focus:ring-primary-100"
            >
              {ORDERING_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>{option.label}</option>
              ))}
            </select>
          </label>
          <Button
            type="button"
            variant="outline"
            onClick={clearFilters}
            disabled={!hasActiveFilters}
            className="w-full lg:w-auto"
          >
            <RotateCcw /> Xóa bộ lọc
          </Button>
        </div>
      </section>

      {loading ? (
        <ApplicationsSkeleton />
      ) : state.error ? (
        <section className="mt-6 rounded-2xl border border-red-200 bg-red-50 p-8 text-center">
          <h2 className="font-semibold text-red-800">Không thể tải đơn ứng tuyển</h2>
          <p className="mt-2 text-sm text-red-700">{state.error}</p>
          <Button type="button" variant="outline" className="mt-5" onClick={() => setReloadKey((value) => value + 1)}>
            Thử lại
          </Button>
        </section>
      ) : result && result.results.length > 0 ? (
        <section className="mt-6 space-y-4" aria-label="Danh sách đơn ứng tuyển">
          {result.results.map((item) => (
            <ApplicationCard key={item.id} item={item} detailSuffix={detailSuffix} />
          ))}
        </section>
      ) : status ? (
        <section className="mt-6 rounded-2xl border border-dashed border-zinc-300 bg-white px-5 py-12 text-center">
          <FileText className="mx-auto size-9 text-zinc-300" />
          <h2 className="mt-4 font-semibold text-zinc-800">Không có kết quả</h2>
          <p className="mt-2 text-sm text-zinc-500">Không có đơn ứng tuyển phù hợp với bộ lọc hiện tại.</p>
          <Button type="button" variant="outline" className="mt-5" onClick={clearFilters}>Xóa bộ lọc</Button>
        </section>
      ) : (
        <section className="mt-6 rounded-2xl border border-dashed border-zinc-300 bg-white px-5 py-12 text-center">
          <FileText className="mx-auto size-9 text-zinc-300" />
          <h2 className="mt-4 font-semibold text-zinc-800">Bạn chưa có đơn ứng tuyển</h2>
          <p className="mt-2 text-sm text-zinc-500">Hãy tìm một công việc phù hợp và bắt đầu ứng tuyển.</p>
          <Button asChild className="mt-5"><Link href="/jobs">Tìm việc làm</Link></Button>
        </section>
      )}

      {!loading && !state.error && result && (
        <Pagination
          page={page}
          hasPrevious={Boolean(result.previous)}
          hasNext={Boolean(result.next)}
          onPage={(nextPage) => updateQuery({ page: nextPage })}
        />
      )}
    </div>
  );
}

function ApplicationCard({
  item,
  detailSuffix,
}: {
  item: CandidateApplicationDto;
  detailSuffix: string;
}) {
  const href = `/candidate/applications/${item.id}${detailSuffix}`;
  return (
    <article className="group relative overflow-hidden rounded-2xl border border-zinc-200 bg-white p-5 shadow-sm transition-colors hover:border-blue-300 hover:bg-blue-50/30 sm:p-6">
      <Link href={href} className="absolute inset-0" tabIndex={-1} aria-hidden="true" />
      <div className="flex flex-col gap-5 md:flex-row md:items-center">
        <div className="grid size-12 shrink-0 place-items-center rounded-xl bg-primary text-lg font-bold text-white shadow-sm">
          {item.company_name.charAt(0).toUpperCase()}
        </div>
        <div className="min-w-0 flex-1">
          <h2 className="truncate text-lg font-semibold text-zinc-900 group-hover:text-primary">{item.job_title}</h2>
          <p className="mt-1 truncate text-sm font-medium text-zinc-600">{item.company_name}</p>
          <div className="mt-3 flex flex-col gap-2 text-sm text-zinc-500 sm:flex-row sm:flex-wrap sm:items-center sm:gap-x-5">
            <span className="inline-flex items-center gap-2"><CalendarDays className="size-4" />Nộp ngày {formatApplicationDate(item.created_at)}</span>
            <span className="truncate">CV: {item.submitted_resume?.original_filename ?? "Không đính kèm"}</span>
          </div>
        </div>
        <div className="flex shrink-0 flex-col gap-3 md:w-44 md:items-end">
          <ApplicationStatusBadge status={item.status} />
          <p className="text-sm text-zinc-500">
            Điểm phù hợp:{" "}
            <span className="font-medium text-zinc-700">
              {item.match_status === "PENDING" || item.match_status === "PROCESSING"
                ? "Đang cập nhật"
                : matchStatusLabel[item.match_status]}
            </span>
          </p>
          <Button asChild size="sm" className="relative z-10 w-full md:w-auto">
            <Link href={href}>Xem chi tiết</Link>
          </Button>
        </div>
      </div>
    </article>
  );
}

function ApplicationsSkeleton() {
  return (
    <div className="mt-6 space-y-4" aria-label="Đang tải đơn ứng tuyển" aria-busy="true">
      {[0, 1, 2].map((item) => (
        <div key={item} className="rounded-2xl border border-zinc-200 bg-white p-5 sm:p-6">
          <div className="flex flex-col gap-5 md:flex-row md:items-center">
            <div className="size-12 animate-pulse rounded-xl bg-zinc-100" />
            <div className="flex-1 space-y-3">
              <div className="h-5 w-2/3 animate-pulse rounded bg-zinc-100" />
              <div className="h-4 w-1/3 animate-pulse rounded bg-zinc-100" />
              <div className="h-4 w-3/4 animate-pulse rounded bg-zinc-100" />
            </div>
            <div className="h-20 w-full animate-pulse rounded-xl bg-zinc-100 md:w-44" />
          </div>
        </div>
      ))}
    </div>
  );
}

function Pagination({
  page,
  hasPrevious,
  hasNext,
  onPage,
}: {
  page: number;
  hasPrevious: boolean;
  hasNext: boolean;
  onPage: (page: number) => void;
}) {
  return (
    <nav className="mt-8 flex flex-wrap items-center justify-center gap-3" aria-label="Phân trang đơn ứng tuyển">
      <Button type="button" variant="outline" disabled={!hasPrevious} onClick={() => onPage(page - 1)}>Trang trước</Button>
      <span className="min-w-20 text-center text-sm font-medium text-zinc-600">Trang {page}</span>
      <Button type="button" variant="outline" disabled={!hasNext} onClick={() => onPage(page + 1)}>Trang sau</Button>
    </nav>
  );
}
