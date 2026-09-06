"use client";

import { ArrowLeft, Download } from "lucide-react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import {
  getApplicationResumeDownloadURL,
  getCandidateApplication,
} from "@/features/applications/api";
import {
  ApplicationStatusBadge,
  applicationStatusLabel,
  matchStatusLabel,
} from "@/features/applications/components/status-badge";
import type { CandidateApplicationDto } from "@/features/applications/types";
import { openPrivateFile } from "@/lib/open-private-file";

export function CandidateApplicationDetail({ id }: { id: string }) {
  const searchParams = useSearchParams();
  const [reloadKey, setReloadKey] = useState(0);
  const requestKey = `${id}|${reloadKey}`;
  const [state, setState] = useState<{
    requestKey: string;
    item: CandidateApplicationDto | null;
    error: string | null;
  }>({ requestKey: "", item: null, error: null });
  const [downloadError, setDownloadError] = useState<string | null>(null);
  const listQuery = new URLSearchParams();
  for (const key of ["status", "ordering", "page"]) {
    const value = searchParams.get(key);
    if (value) listQuery.set(key, value);
  }
  const listHref = `/candidate/applications${listQuery.size ? `?${listQuery}` : ""}`;
  const loading = state.requestKey !== requestKey;
  const item = state.item;

  useEffect(() => {
    const controller = new AbortController();
    getCandidateApplication(id, controller.signal)
      .then((result) => setState({ requestKey, item: result, error: null }))
      .catch((reason: unknown) => {
        if (controller.signal.aborted) return;
        setState({
          requestKey,
          item: null,
          error: reason instanceof Error ? reason.message : "Không thể tải đơn.",
        });
      });
    return () => controller.abort();
  }, [id, requestKey]);

  const viewResume = async () => {
    setDownloadError(null);
    try {
      await openPrivateFile(() => getApplicationResumeDownloadURL(id));
    } catch (reason) {
      setDownloadError(reason instanceof Error ? reason.message : "Không thể mở CV.");
    }
  };

  if (loading) {
    return <div className="mx-auto mt-8 h-64 max-w-3xl animate-pulse rounded-xl bg-zinc-100" aria-label="Đang tải chi tiết đơn ứng tuyển" aria-busy="true" />;
  }
  if (state.error) {
    return (
      <div className="mx-auto max-w-3xl px-4 py-8 sm:px-6">
        <Button asChild variant="ghost" size="sm"><Link href={listHref}><ArrowLeft />Danh sách đơn</Link></Button>
        <div className="mt-4 rounded-xl border border-red-200 bg-red-50 p-6 text-center" role="alert">
          <p className="text-sm text-red-700">{state.error}</p>
          <Button type="button" variant="outline" className="mt-4" onClick={() => setReloadKey((value) => value + 1)}>Thử lại</Button>
        </div>
      </div>
    );
  }
  if (!item) {
    return <div className="mx-auto mt-8 h-64 max-w-3xl animate-pulse rounded-xl bg-zinc-100" aria-label="Đang tải chi tiết đơn ứng tuyển" aria-busy="true" />;
  }

  return (
    <div className="mx-auto max-w-4xl px-4 py-7 sm:px-6 lg:px-8">
      <Button asChild variant="ghost" size="sm">
        <Link href={listHref}><ArrowLeft />Danh sách đơn</Link>
      </Button>
      {downloadError && <p className="mt-4 rounded-xl bg-red-50 p-4 text-sm text-red-600">{downloadError}</p>}
      <div className="mt-4 rounded-xl border border-zinc-200 bg-white p-5 shadow-sm sm:p-7">
        <div className="flex flex-col justify-between gap-3 sm:flex-row">
          <div>
            <p className="text-sm font-medium text-primary">{item.company_name}</p>
            <h1 className="mt-1 text-2xl font-bold text-zinc-900">{item.job_title}</h1>
          </div>
          <ApplicationStatusBadge status={item.status} />
        </div>
        <p className="mt-4 rounded-lg bg-zinc-50 px-3 py-2 text-xs text-zinc-600">
          {matchStatusLabel[item.match_status]}
        </p>
        {item.cover_letter && (
          <section className="mt-6 border-t border-zinc-100 pt-5">
            <h2 className="font-semibold text-zinc-900">Thư giới thiệu</h2>
            <p className="mt-2 whitespace-pre-line text-sm leading-6 text-zinc-600">{item.cover_letter}</p>
          </section>
        )}
        {item.submitted_resume && (
          <section className="mt-5 flex flex-col gap-3 rounded-xl bg-zinc-50 p-4 sm:flex-row sm:items-center sm:justify-between">
            <div className="min-w-0">
              <p className="text-sm font-medium text-zinc-800">CV đã nộp</p>
              <p className="mt-1 break-all text-xs text-zinc-500">{item.submitted_resume.original_filename}</p>
            </div>
            <Button type="button" variant="outline" size="sm" onClick={() => void viewResume()}>
              <Download />Xem CV
            </Button>
          </section>
        )}
        {!item.submitted_resume && (
          <p className="mt-5 rounded-xl bg-zinc-50 p-4 text-sm text-zinc-500">
            Đơn này không đính kèm tệp CV.
          </p>
        )}
        <section className="mt-7">
          <h2 className="font-semibold text-zinc-900">Lịch sử trạng thái</h2>
          <div className="mt-4 space-y-0">
            {item.history.map((history, index) => (
              <div key={history.id} className="relative flex gap-3 pb-5 last:pb-0">
                {index < item.history.length - 1 && <span className="absolute left-2 top-4 h-full w-px bg-zinc-200" />}
                <span className="relative mt-1 size-4 rounded-full border-4 border-primary-100 bg-primary" />
                <div>
                  <p className="text-sm font-medium text-zinc-800">{applicationStatusLabel[history.to_status]}</p>
                  <p className="mt-1 text-xs text-zinc-400">{new Date(history.created_at).toLocaleString("vi-VN")}</p>
                  {history.candidate_message && <p className="mt-1 text-sm text-zinc-500">{history.candidate_message}</p>}
                </div>
              </div>
            ))}
          </div>
        </section>
      </div>
    </div>
  );
}
