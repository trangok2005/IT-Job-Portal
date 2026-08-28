"use client";

import { BriefcaseBusiness, Plus, UsersRound } from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  closeEmployerJob,
  getMyCompany,
  getMyJobs,
  publishEmployerJob,
} from "@/features/employer/api";
import type { CompanyStatus, EmployerJobDto } from "@/features/employer/types";

export function EmployerJobs() {
  const [items, setItems] = useState<EmployerJobDto[]>([]);
  const [companyStatus, setCompanyStatus] = useState<CompanyStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);

  const load = async () => {
    const result = await getMyJobs();
    setItems(result.results);
  };

  useEffect(() => {
    Promise.all([getMyJobs(), getMyCompany()])
      .then(([jobs, company]) => {
        setItems(jobs.results);
        setCompanyStatus(company.status);
      })
      .catch((reason: unknown) => setError(reason instanceof Error ? reason.message : "Không thể tải tin tuyển dụng."))
      .finally(() => setLoading(false));
  }, []);

  const act = async (job: EmployerJobDto, action: "publish" | "close") => {
    if (action === "close" && !window.confirm(`Đóng tin “${job.title}”? Trạng thái này không thể hoàn tác.`)) return;
    setBusyId(job.id);
    setError(null);
    try {
      if (action === "publish") await publishEmployerJob(job.id);
      else await closeEmployerJob(job.id);
      await load();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Không thể cập nhật tin tuyển dụng.");
    } finally {
      setBusyId(null);
    }
  };

  return (
    <div className="mx-auto max-w-6xl px-4 py-7 sm:px-6 lg:px-8">
      <div className="flex items-end justify-between gap-4">
        <div><h1 className="text-2xl font-bold text-zinc-900">Tin tuyển dụng</h1><p className="mt-1 text-sm text-zinc-500">Quản lý draft, tin đang chạy và ứng viên.</p></div>
        {companyStatus === "APPROVED" && <Button asChild variant="accent"><Link href="/employer/jobs/new"><Plus />Tạo tin</Link></Button>}
      </div>
      {companyStatus && companyStatus !== "APPROVED" && <p className="mt-5 rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-800">Công ty đang ở trạng thái <strong>{companyStatus}</strong>. Bạn vẫn có thể xem tin và xử lý hồ sơ cũ, nhưng chưa thể tạo hoặc đăng tin mới.</p>}
      {error && <p className="mt-5 rounded-xl bg-red-50 p-4 text-sm text-red-700">{error}</p>}
      {loading && <div className="mt-6 h-48 animate-pulse rounded-xl bg-zinc-100" />}
      {!loading && <div className="mt-6 space-y-3">
        {items.map((job) => (
          <article key={job.id} className="rounded-xl border border-zinc-200 bg-white p-4 shadow-sm sm:p-5">
            <div className="flex flex-col gap-4 sm:flex-row sm:items-center">
              <span className="grid size-11 shrink-0 place-items-center rounded-xl bg-primary-50 text-primary"><BriefcaseBusiness /></span>
              <div className="min-w-0 flex-1"><div className="flex flex-wrap items-center gap-2"><h2 className="font-semibold text-zinc-900">{job.title}</h2><Badge variant={job.status === "ACTIVE" ? "success" : "outline"}>{job.status}</Badge></div><p className="mt-1 text-sm text-zinc-500">{job.location || "Không giới hạn địa điểm"} · {job.application_count} ứng viên</p></div>
              <div className="flex flex-wrap gap-2">
                <Button asChild size="sm" variant="outline"><Link href={`/employer/jobs/${job.id}/applications`}><UsersRound />Ứng viên</Link></Button>
                {job.status === "DRAFT" && <Button asChild size="sm" variant="ghost"><Link href={`/employer/jobs/${job.id}/edit`}>Sửa</Link></Button>}
                {job.status === "DRAFT" && companyStatus === "APPROVED" && <Button size="sm" disabled={busyId === job.id} onClick={() => void act(job, "publish")}>{busyId === job.id ? "Đang đăng..." : "Đăng tin"}</Button>}
                {job.status === "ACTIVE" && <Button size="sm" variant="outline" disabled={busyId === job.id} onClick={() => void act(job, "close")}>{busyId === job.id ? "Đang đóng..." : "Đóng tin"}</Button>}
              </div>
            </div>
          </article>
        ))}
      </div>}
      {!loading && items.length === 0 && <div className="mt-6 rounded-xl border border-dashed border-zinc-200 bg-white p-10 text-center text-sm text-zinc-500">Chưa có tin tuyển dụng nào.</div>}
    </div>
  );
}
