"use client";

import { FileText } from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { getCandidateApplications } from "@/features/applications/api";
import { ApplicationStatusBadge } from "@/features/applications/components/status-badge";
import type { CandidateApplicationDto } from "@/features/applications/types";

export function CandidateApplications() {
  const [items, setItems] = useState<CandidateApplicationDto[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => { getCandidateApplications().then((result) => setItems(result.results)).catch((err: unknown) => setError(err instanceof Error ? err.message : "Không thể tải đơn ứng tuyển.")).finally(() => setLoading(false)); }, []);
  return (
    <div className="mx-auto max-w-5xl px-4 py-7 sm:px-6 lg:px-8">
      <h1 className="text-2xl font-bold text-zinc-900">Đơn ứng tuyển</h1><p className="mt-1 text-sm text-zinc-500">Theo dõi tiến trình và phản hồi từ nhà tuyển dụng.</p>
      {error && <p className="mt-5 rounded-xl bg-red-50 p-4 text-sm text-red-600">{error}</p>}
      {loading ? <div className="mt-6 h-48 animate-pulse rounded-xl bg-zinc-100" /> : items.length ? <div className="mt-6 space-y-3">{items.map((item) => <Link key={item.id} href={`/candidate/applications/${item.id}`} className="flex flex-col gap-4 rounded-xl border border-zinc-200 bg-white p-4 shadow-sm transition hover:border-primary-200 hover:shadow-md sm:flex-row sm:items-center"><span className="grid size-11 shrink-0 place-items-center rounded-xl bg-primary-50 font-bold text-primary">{item.company_name.charAt(0)}</span><div className="min-w-0 flex-1"><h2 className="truncate font-semibold text-zinc-900">{item.job_title}</h2><p className="mt-1 text-sm text-zinc-500">{item.company_name} · Nộp {new Date(item.created_at).toLocaleDateString("vi-VN")}</p></div><ApplicationStatusBadge status={item.status} /></Link>)}</div> : <div className="mt-6 rounded-xl border border-dashed border-zinc-200 bg-white p-10 text-center"><FileText className="mx-auto size-8 text-zinc-300" /><p className="mt-3 text-sm text-zinc-500">Bạn chưa có đơn ứng tuyển nào.</p><Button asChild className="mt-4"><Link href="/jobs">Tìm việc ngay</Link></Button></div>}
    </div>
  );
}
