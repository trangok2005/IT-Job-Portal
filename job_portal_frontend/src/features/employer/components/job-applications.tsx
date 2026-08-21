"use client";

import { Sparkles, UserRound } from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { getJobApplications } from "@/features/applications/api";
import { ApplicationStatusBadge } from "@/features/applications/components/status-badge";
import type { ApplicationStatus, EmployerApplicationDto } from "@/features/applications/types";
import { getRecommendedCandidates } from "@/features/employer/api";
import type { RecommendedCandidateDto } from "@/features/employer/types";

export function JobApplications({ jobId }: { jobId: string }) {
  const [items, setItems] = useState<EmployerApplicationDto[]>([]);
  const [recommended, setRecommended] = useState<RecommendedCandidateDto[]>([]);
  const [status, setStatus] = useState<ApplicationStatus | "">("");
  const [ordering, setOrdering] = useState("-match_score");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    getJobApplications(jobId, status, ordering)
      .then((response) => {
        if (active) setItems(response.results);
      })
      .catch((reason: unknown) => {
        if (active) setError(reason instanceof Error ? reason.message : "Không thể tải hồ sơ ứng tuyển.");
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => { active = false; };
  }, [jobId, ordering, status]);

  useEffect(() => {
    let active = true;
    getRecommendedCandidates(jobId)
      .then((response) => {
        if (active) setRecommended(response.results);
      })
      .catch(() => undefined);
    return () => { active = false; };
  }, [jobId]);

  const changeStatus = (value: string) => {
    setLoading(true);
    setError(null);
    setStatus(value as ApplicationStatus | "");
  };

  const changeOrdering = (value: string) => {
    setLoading(true);
    setError(null);
    setOrdering(value);
  };

  return (
    <div className="mx-auto max-w-6xl px-4 py-7 sm:px-6 lg:px-8">
      <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-end">
        <div><h1 className="text-2xl font-bold text-zinc-900">Ứng viên của tin</h1><p className="mt-1 text-sm text-zinc-500">AI chỉ xếp hạng, quyết định trạng thái luôn thuộc nhà tuyển dụng.</p></div>
        <div className="flex flex-wrap gap-2">
          <select value={status} onChange={(event) => changeStatus(event.target.value)} className="h-10 rounded-xl border border-zinc-300 bg-white px-3 text-sm"><option value="">Tất cả trạng thái</option>{["APPLIED", "SHORTLISTED", "INTERVIEWED", "HIRED", "REJECTED"].map((value) => <option key={value} value={value}>{value}</option>)}</select>
          <select value={ordering} onChange={(event) => changeOrdering(event.target.value)} className="h-10 rounded-xl border border-zinc-300 bg-white px-3 text-sm"><option value="-match_score">Match score cao nhất</option><option value="-created_at">Mới nhất</option><option value="created_at">Cũ nhất</option></select>
        </div>
      </div>
      {error && <p className="mt-4 rounded-xl bg-red-50 p-4 text-sm text-red-700">{error}</p>}

      <section className="mt-6">
        <h2 className="font-semibold text-zinc-900">Hồ sơ đã ứng tuyển</h2>
        {loading ? <div className="mt-3 h-40 animate-pulse rounded-xl bg-zinc-100" /> : items.length === 0 ? <p className="mt-3 rounded-xl border border-dashed border-zinc-300 p-10 text-center text-sm text-zinc-500">Không có hồ sơ phù hợp bộ lọc.</p> : (
          <div className="mt-3 space-y-3">
            {items.map((item) => (
              <Link key={item.id} href={`/employer/jobs/${jobId}/applications/${item.id}`} className="flex flex-col gap-3 rounded-xl border border-zinc-200 bg-white p-4 shadow-sm hover:border-primary-200 sm:flex-row sm:items-center">
                <span className="grid size-11 place-items-center rounded-xl bg-primary-50 font-bold text-primary">{item.candidate_name.charAt(0)}</span>
                <div className="min-w-0 flex-1"><h3 className="font-semibold text-zinc-900">{item.candidate_name}</h3><p className="mt-1 truncate text-sm text-zinc-500">{item.candidate_headline || item.candidate_email}</p></div>
                <div className="flex items-center gap-3"><span className="font-bold text-accent">{item.match_score === null ? "Đang tính" : `${item.match_score}%`}</span><ApplicationStatusBadge status={item.status} /></div>
              </Link>
            ))}
          </div>
        )}
      </section>

      {recommended.length > 0 && <section className="mt-9"><div className="flex items-center gap-2"><Sparkles className="size-5 text-accent" /><h2 className="font-semibold text-zinc-900">Ứng viên gợi ý</h2></div><p className="mt-1 text-sm text-zinc-500">Chỉ hiển thị hồ sơ công khai, không lộ thông tin liên hệ.</p><div className="mt-3 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">{recommended.slice(0, 6).map((candidate) => <div key={candidate.id} className="rounded-xl border border-zinc-200 bg-white p-4 shadow-sm"><div className="flex items-start justify-between"><UserRound className="text-primary" /><Badge variant="accent">{candidate.match_score === null ? "Đang tính" : `${candidate.match_score.toFixed(0)}%`}</Badge></div><h3 className="mt-3 font-semibold">{candidate.full_name}</h3><p className="mt-1 text-sm text-zinc-500">{candidate.headline || candidate.desired_position}</p><div className="mt-3 flex flex-wrap gap-1">{candidate.skills.slice(0, 4).map((skill) => <Badge key={skill} variant="outline">{skill}</Badge>)}</div></div>)}</div></section>}
    </div>
  );
}
