"use client";

import { BriefcaseBusiness, Building2, FileText, Plus, UsersRound } from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { getEmployerDashboard } from "@/features/dashboard/api";
import type { EmployerDashboardDto } from "@/features/dashboard/types";

export function EmployerDashboard() {
  const [data, setData] = useState<EmployerDashboardDto | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getEmployerDashboard()
      .then(setData)
      .catch((reason: unknown) => setError(reason instanceof Error ? reason.message : "Không thể tải dashboard."));
  }, []);

  if (error) return <div className="mx-auto max-w-6xl px-4 py-8"><p className="rounded-xl bg-red-50 p-4 text-sm text-red-700">{error}</p></div>;
  if (!data) return <div className="mx-auto mt-8 h-64 max-w-6xl animate-pulse rounded-xl bg-zinc-100" />;

  const stats = [
    ["Tổng tin", data.jobs_total, BriefcaseBusiness],
    ["Tin đang chạy", data.jobs_active, FileText],
    ["Tin nháp", data.jobs_draft, Building2],
    ["Chờ xử lý", data.new_applications, UsersRound],
  ] as const;

  return (
    <div className="mx-auto max-w-6xl px-4 py-7 sm:px-6 lg:px-8">
      <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-end">
        <div><p className="text-sm font-medium text-accent">Không gian tuyển dụng</p><h1 className="mt-1 text-3xl font-bold text-zinc-900">Tổng quan tuyển dụng</h1><p className="mt-1 text-sm text-zinc-500">Trạng thái công ty: <strong>{data.company_status ?? "Chưa cập nhật"}</strong></p></div>
        {data.company_status === "APPROVED" && <Button asChild variant="accent"><Link href="/employer/jobs/new"><Plus />Đăng tin mới</Link></Button>}
      </div>
      <div className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {stats.map(([label, value, Icon]) => <div key={label} className="rounded-xl border border-zinc-200 bg-white p-5 shadow-sm"><Icon className="size-5 text-primary" /><p className="mt-4 text-2xl font-bold text-zinc-900">{value}</p><p className="mt-1 text-sm text-zinc-500">{label}</p></div>)}
      </div>
      <p className="mt-4 text-sm text-zinc-500">Tổng hồ sơ đã nhận: <strong className="text-zinc-800">{data.total_applications}</strong></p>
      <div className="mt-7 grid gap-4 sm:grid-cols-2">
        <Link href="/employer/company" className="rounded-xl border border-zinc-200 bg-white p-5 shadow-sm hover:border-primary-200"><Building2 className="text-primary" /><h2 className="mt-3 font-semibold">Hồ sơ công ty</h2><p className="mt-1 text-sm text-zinc-500">Cập nhật thông tin và theo dõi phê duyệt.</p></Link>
        <Link href="/employer/jobs" className="rounded-xl border border-zinc-200 bg-white p-5 shadow-sm hover:border-primary-200"><BriefcaseBusiness className="text-primary" /><h2 className="mt-3 font-semibold">Quản lý tin tuyển dụng</h2><p className="mt-1 text-sm text-zinc-500">Theo dõi trạng thái và hồ sơ ứng viên.</p></Link>
      </div>
    </div>
  );
}
