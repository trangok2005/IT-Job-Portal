"use client";

import { ArrowLeft, Download } from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { getCandidateApplication } from "@/features/applications/api";
import { ApplicationStatusBadge, applicationStatusLabel } from "@/features/applications/components/status-badge";
import type { CandidateApplicationDto } from "@/features/applications/types";

export function CandidateApplicationDetail({ id }: { id: string }) {
  const [item, setItem] = useState<CandidateApplicationDto | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => { getCandidateApplication(id).then(setItem).catch((err: unknown) => setError(err instanceof Error ? err.message : "Không thể tải đơn.")); }, [id]);
  if (error) return <p className="mx-auto mt-8 max-w-3xl rounded-xl bg-red-50 p-4 text-sm text-red-600">{error}</p>;
  if (!item) return <div className="mx-auto mt-8 h-64 max-w-3xl animate-pulse rounded-xl bg-zinc-100" />;
  return <div className="mx-auto max-w-4xl px-4 py-7 sm:px-6 lg:px-8"><Button asChild variant="ghost" size="sm"><Link href="/candidate/applications"><ArrowLeft />Danh sách đơn</Link></Button><div className="mt-4 rounded-xl border border-zinc-200 bg-white p-5 shadow-sm sm:p-7"><div className="flex flex-col justify-between gap-3 sm:flex-row"><div><p className="text-sm font-medium text-primary">{item.company_name}</p><h1 className="mt-1 text-2xl font-bold text-zinc-900">{item.job_title}</h1></div><ApplicationStatusBadge status={item.status} /></div>{item.cover_letter && <section className="mt-6 border-t border-zinc-100 pt-5"><h2 className="font-semibold text-zinc-900">Thư giới thiệu</h2><p className="mt-2 whitespace-pre-line text-sm leading-6 text-zinc-600">{item.cover_letter}</p></section>}{item.submitted_resume && <section className="mt-5 flex items-center justify-between rounded-xl bg-zinc-50 p-4"><div><p className="text-sm font-medium text-zinc-800">CV đã nộp</p><p className="mt-1 text-xs text-zinc-500">{item.submitted_resume.original_filename}</p></div><Button asChild variant="outline" size="sm"><a href={item.submitted_resume.file_url} target="_blank" rel="noreferrer"><Download />Xem CV</a></Button></section>}<section className="mt-7"><h2 className="font-semibold text-zinc-900">Lịch sử trạng thái</h2><div className="mt-4 space-y-0">{item.history.map((history, index) => <div key={history.id} className="relative flex gap-3 pb-5 last:pb-0">{index < item.history.length - 1 && <span className="absolute left-2 top-4 h-full w-px bg-zinc-200" />}<span className="relative mt-1 size-4 rounded-full border-4 border-primary-100 bg-primary" /><div><p className="text-sm font-medium text-zinc-800">{applicationStatusLabel[history.to_status]}</p><p className="mt-1 text-xs text-zinc-400">{new Date(history.created_at).toLocaleString("vi-VN")}</p>{history.note && <p className="mt-1 text-sm text-zinc-500">{history.note}</p>}</div></div>)}</div></section></div></div>;
}
