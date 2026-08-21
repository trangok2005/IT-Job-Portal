"use client";

import { AlertTriangle, Download, History, Loader2 } from "lucide-react";
import { useEffect, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  getApplicationAnalysis,
  getEmployerApplication,
  transitionApplication,
} from "@/features/applications/api";
import { ApplicationStatusBadge } from "@/features/applications/components/status-badge";
import type {
  AnalysisDto,
  ApplicationStatus,
  ApplicationTransitionStatus,
  EmployerApplicationDto,
} from "@/features/applications/types";

const nextStatuses: Record<ApplicationStatus, ApplicationTransitionStatus[]> = {
  APPLIED: ["SHORTLISTED", "REJECTED"],
  SHORTLISTED: ["INTERVIEWED", "REJECTED"],
  INTERVIEWED: ["HIRED", "REJECTED"],
  HIRED: [],
  REJECTED: [],
};

export function EmployerApplicationDetail({ id, jobId }: { id: string; jobId: string }) {
  const [item, setItem] = useState<EmployerApplicationDto | null>(null);
  const [analysis, setAnalysis] = useState<AnalysisDto | null>(null);
  const [loading, setLoading] = useState(true);
  const [analysisError, setAnalysisError] = useState(false);
  const [busy, setBusy] = useState(false);
  const [note, setNote] = useState("");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    getEmployerApplication(id)
      .then((application) => {
        if (!active) return;
        if (application.job_id !== jobId) {
          setError("Hồ sơ ứng tuyển không thuộc tin tuyển dụng trong URL.");
          return;
        }
        setItem(application);
      })
      .catch((reason: unknown) => {
        if (active) setError(reason instanceof Error ? reason.message : "Không thể tải hồ sơ ứng tuyển.");
      })
      .finally(() => {
        if (active) setLoading(false);
      });

    getApplicationAnalysis(id)
      .then((result) => {
        if (active) setAnalysis(result);
      })
      .catch(() => {
        if (active) setAnalysisError(true);
      });
    return () => { active = false; };
  }, [id, jobId]);

  const move = async (status: ApplicationTransitionStatus) => {
    setBusy(true);
    setError(null);
    try {
      setItem(await transitionApplication(id, status, note));
      setNote("");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Không thể đổi trạng thái.");
    } finally {
      setBusy(false);
    }
  };

  if (loading) return <div className="mx-auto mt-8 h-72 max-w-5xl animate-pulse rounded-xl bg-zinc-100" />;
  if (!item) return <div className="mx-auto max-w-3xl px-4 py-12"><p className="rounded-xl bg-red-50 p-4 text-sm text-red-700">{error ?? "Không tìm thấy hồ sơ ứng tuyển."}</p></div>;

  return (
    <div className="mx-auto max-w-5xl px-4 py-7 sm:px-6 lg:px-8">
      {error && <p className="mb-4 rounded-xl bg-red-50 p-4 text-sm text-red-700">{error}</p>}
      <div className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_320px]">
        <div className="space-y-5">
          <section className="rounded-xl border border-zinc-200 bg-white p-5 shadow-sm sm:p-7">
            <div className="flex items-start justify-between gap-4"><div><h1 className="text-2xl font-bold text-zinc-900">{item.candidate_name}</h1><p className="mt-1 text-sm text-primary">{item.candidate_headline}</p><p className="mt-1 text-sm text-zinc-500">{item.candidate_email} · {item.candidate_phone}</p></div><ApplicationStatusBadge status={item.status} /></div>
            <p className="mt-5 whitespace-pre-line text-sm leading-6 text-zinc-600">{item.candidate_summary || "Ứng viên chưa cập nhật phần giới thiệu."}</p>
            <div className="mt-4 flex flex-wrap gap-2">{item.candidate_skills.map((skill) => <Badge key={skill.id} variant="outline">{skill.skill_name}</Badge>)}</div>
            {item.cover_letter && <section className="mt-6 border-t border-zinc-100 pt-5"><h2 className="font-semibold">Thư giới thiệu</h2><p className="mt-2 whitespace-pre-line text-sm text-zinc-600">{item.cover_letter}</p></section>}
            {item.submitted_resume && <Button asChild variant="outline" className="mt-5"><a href={item.submitted_resume.file_url} target="_blank" rel="noreferrer"><Download />Xem CV đã nộp</a></Button>}
          </section>

          <section className="rounded-xl border border-zinc-200 bg-white p-5 shadow-sm">
            <div className="flex items-center gap-2"><History className="size-4 text-primary" /><h2 className="font-semibold text-zinc-900">Lịch sử xử lý</h2></div>
            <div className="mt-4 space-y-3">
              {item.history.map((entry) => <div key={entry.id} className="border-l-2 border-primary-100 pl-3 text-sm"><p className="font-medium text-zinc-800">{entry.from_status || "Khởi tạo"} → {entry.to_status}</p><p className="mt-0.5 text-xs text-zinc-400">{new Date(entry.created_at).toLocaleString("vi-VN")} · {entry.changed_by_email}</p>{entry.note && <p className="mt-1 text-xs text-zinc-600">{entry.note}</p>}</div>)}
            </div>
          </section>
        </div>

        <aside className="space-y-4">
          <section className="rounded-xl border border-zinc-200 bg-white p-5 shadow-sm">
            <p className="text-sm font-medium text-zinc-500">AI match score</p>
            <p className="mt-2 text-4xl font-bold text-accent">{analysis?.match_score ?? item.match_score ?? "--"}<span className="text-lg">%</span></p>
            {analysisError && <p className="mt-3 text-xs text-amber-700">Không thể tải chi tiết phân tích.</p>}
            {analysis?.inputs_are_stale && <p className="mt-3 flex gap-2 rounded-lg bg-amber-50 p-3 text-xs text-amber-800"><AlertTriangle className="size-4 shrink-0" />Kết quả này đã cũ do hồ sơ hoặc tin tuyển dụng thay đổi.</p>}
            {analysis && <div className="mt-4"><p className="text-xs font-medium text-emerald-700">Kỹ năng phù hợp</p><div className="mt-2 flex flex-wrap gap-1">{analysis.matched_skills.map((skill) => <Badge key={skill} variant="success">{skill}</Badge>)}</div><p className="mt-3 text-xs font-medium text-red-600">Kỹ năng còn thiếu</p><div className="mt-2 flex flex-wrap gap-1">{analysis.missing_skills.map((skill) => <Badge key={skill} variant="outline">{skill}</Badge>)}</div></div>}
          </section>

          {nextStatuses[item.status].length > 0 && <section className="rounded-xl border border-zinc-200 bg-white p-5 shadow-sm"><h2 className="font-semibold text-zinc-900">Cập nhật trạng thái</h2><textarea value={note} onChange={(event) => setNote(event.target.value)} placeholder="Ghi chú nội bộ hoặc nội dung thông báo..." className="mt-3 min-h-24 w-full rounded-xl border border-zinc-300 p-3 text-sm outline-none focus:border-primary" /><div className="mt-3 grid gap-2">{nextStatuses[item.status].map((status) => <Button key={status} variant={status === "REJECTED" ? "outline" : "default"} disabled={busy} onClick={() => void move(status)}>{busy && <Loader2 className="animate-spin" />}{status}</Button>)}</div></section>}
        </aside>
      </div>
    </div>
  );
}
