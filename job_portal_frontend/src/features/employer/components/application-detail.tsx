"use client";

import { Download, History, Loader2 } from "lucide-react";
import { useEffect, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  getApplicationMatchResult,
  getApplicationResumeDownloadURL,
  getEmployerApplication,
  transitionApplication,
} from "@/features/applications/api";
import {
  ApplicationStatusBadge,
  applicationStatusLabel,
  matchStatusLabel,
} from "@/features/applications/components/status-badge";
import type {
  ApplicationMatchResultDto,
  ApplicationStatus,
  ApplicationTransitionStatus,
  EmployerApplicationDto,
  MatchStatus,
} from "@/features/applications/types";
import { openPrivateFile } from "@/lib/open-private-file";

const nextStatuses: Record<ApplicationStatus, ApplicationTransitionStatus[]> = {
  APPLIED: ["SHORTLISTED", "REJECTED"],
  SHORTLISTED: ["INTERVIEWED", "REJECTED"],
  INTERVIEWED: ["HIRED", "REJECTED"],
  HIRED: [],
  REJECTED: [],
};

const matchComponents = [
  ["semantic", "Mức độ tương đồng nội dung", "semantic_similarity_score"],
  ["skill", "Mức độ phù hợp kỹ năng", "skill_overlap_score"],
  ["experience", "Mức độ phù hợp kinh nghiệm", "experience_score"],
  ["education", "Mức độ phù hợp học vấn", "education_score"],
] as const;

function formatComponentScore(value: string | null, ruleVersion: string) {
  if (value === null) return null;
  const score = Number(value);
  const percentage = ruleVersion === "legacy-v1" ? score : score * 100;
  return Number.isFinite(percentage)
    ? new Intl.NumberFormat("vi-VN", { maximumFractionDigits: 1 }).format(percentage) + "%"
    : null;
}

function detailReason(value: unknown) {
  return typeof value === "string" && value.trim() ? value : null;
}

function formatSnapshotDate(value: string) {
  const date = new Date(value);
  return new Intl.DateTimeFormat("en-GB", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
  }).format(date).replaceAll("/", "-");
}

export function EmployerApplicationDetail({ id, jobId }: { id: string; jobId: string }) {
  const [item, setItem] = useState<EmployerApplicationDto | null>(null);
  const [matchResult, setMatchResult] = useState<ApplicationMatchResultDto | null>(null);
  const [loading, setLoading] = useState(true);
  const [matchResultError, setMatchResultError] = useState(false);
  const [busy, setBusy] = useState(false);
  const [note, setNote] = useState("");
  const [candidateMessage, setCandidateMessage] = useState("");
  const [selectedStatus, setSelectedStatus] = useState<ApplicationTransitionStatus | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

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

    getApplicationMatchResult(id)
      .then((result) => {
        if (active) setMatchResult(result);
      })
      .catch(() => {
        if (active) setMatchResultError(true);
      });
    return () => { active = false; };
  }, [id, jobId]);

  const move = async () => {
    if (!selectedStatus || !item) return;
    setBusy(true);
    setError(null);
    setSuccess(null);
    try {
      setItem(await transitionApplication(id, {
        status: selectedStatus,
        expected_status: item.status,
        note,
        candidate_message: candidateMessage,
      }));
      setNote("");
      setCandidateMessage("");
      setSelectedStatus(null);
      setSuccess("Đã cập nhật trạng thái. Email thông báo đang được gửi đến ứng viên.");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Không thể đổi trạng thái.");
    } finally {
      setBusy(false);
    }
  };

  const viewResume = async () => {
    setError(null);
    try {
      await openPrivateFile(() => getApplicationResumeDownloadURL(id));
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Không thể mở CV.");
    }
  };

  if (loading) return <div className="mx-auto mt-8 h-72 max-w-5xl animate-pulse rounded-xl bg-zinc-100" />;
  if (!item) return <div className="mx-auto max-w-3xl px-4 py-12"><p className="rounded-xl bg-red-50 p-4 text-sm text-red-700">{error ?? "Không tìm thấy hồ sơ ứng tuyển."}</p></div>;

  const matchScore = matchResult?.match_score ?? item.match_score;
  const snapshotDate = matchResult?.snapshot_created_at ?? item.created_at;
  const resultStatus = matchResult?.status;
  const matchStatus: MatchStatus = resultStatus && resultStatus in matchStatusLabel
    ? resultStatus as MatchStatus
    : item.match_status;

  return (
    <div className="mx-auto max-w-5xl px-4 py-7 sm:px-6 lg:px-8">
      {error && <p className="mb-4 rounded-xl bg-red-50 p-4 text-sm text-red-700">{error}</p>}
      {success && <p className="mb-4 rounded-xl bg-emerald-50 p-4 text-sm text-emerald-700">{success}</p>}
      <div className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_320px]">
        <div className="space-y-5">
          <section className="rounded-xl border border-zinc-200 bg-white p-5 shadow-sm sm:p-7">
            <div className="flex items-start justify-between gap-4"><div><h1 className="text-2xl font-bold text-zinc-900">{item.candidate_name}</h1><p className="mt-1 text-sm text-primary">{item.candidate_headline}</p><p className="mt-1 text-sm text-zinc-500">{item.candidate_email} · {item.candidate_phone}</p></div><ApplicationStatusBadge status={item.status} /></div>
            <p className="mt-5 whitespace-pre-line text-sm leading-6 text-zinc-600">{item.candidate_summary || "Ứng viên chưa cập nhật phần giới thiệu."}</p>
            <div className="mt-4 flex flex-wrap gap-2">{item.candidate_skills.map((skill) => <Badge key={skill.id} variant="outline">{skill.skill_name}</Badge>)}</div>
            {item.cover_letter && <section className="mt-6 border-t border-zinc-100 pt-5"><h2 className="font-semibold">Thư giới thiệu</h2><p className="mt-2 whitespace-pre-line text-sm text-zinc-600">{item.cover_letter}</p></section>}
            {item.submitted_resume && <Button type="button" variant="outline" className="mt-5" onClick={() => void viewResume()}><Download />Xem CV đã nộp</Button>}
          </section>

          <section className="rounded-xl border border-zinc-200 bg-white p-5 shadow-sm">
            <div className="flex items-center gap-2"><History className="size-4 text-primary" /><h2 className="font-semibold text-zinc-900">Lịch sử xử lý</h2></div>
            <div className="mt-4 space-y-3">
              {item.history.map((entry) => <div key={entry.id} className="border-l-2 border-primary-100 pl-3 text-sm"><p className="font-medium text-zinc-800">{entry.from_status || "Khởi tạo"} → {entry.to_status}</p><p className="mt-0.5 text-xs text-zinc-400">{new Date(entry.created_at).toLocaleString("vi-VN")} · {entry.changed_by_email}</p>{entry.note && <p className="mt-1 text-xs text-zinc-600"><span className="font-medium">Nội bộ:</span> {entry.note}</p>}{entry.candidate_message && <p className="mt-1 text-xs text-zinc-600"><span className="font-medium">Gửi ứng viên:</span> {entry.candidate_message}</p>}{entry.notification_status !== "NOT_REQUESTED" && <p className="mt-1 text-xs text-zinc-400">Email: {entry.notification_status === "SENT" ? "Đã gửi" : entry.notification_status === "FAILED" ? "Gửi thất bại, hệ thống sẽ thử lại" : "Đang chờ gửi"}</p>}</div>)}
            </div>
          </section>
        </div>

        <aside className="space-y-4">
          <section className="rounded-xl border border-zinc-200 bg-white p-5 shadow-sm">
            <p className="text-sm font-medium text-zinc-500">Điểm phù hợp</p>
            <p className="mt-2 text-base font-semibold text-zinc-700">{matchStatusLabel[matchStatus]}</p>
            {matchScore !== null && <p className="mt-2 text-4xl font-bold text-accent">{Number(matchScore).toLocaleString("vi-VN", { maximumFractionDigits: 1 })}<span className="text-lg">%</span></p>}
            {item.match_error && <p className="mt-2 text-xs leading-5 text-red-600">{item.match_error}</p>}
            <p className="mt-3 text-xs leading-5 text-zinc-500">Dựa trên hồ sơ tại thời điểm ứng tuyển ngày {formatSnapshotDate(snapshotDate)}</p>
            {matchResultError && <p className="mt-3 text-xs text-amber-700">Không thể tải chi tiết điểm phù hợp.</p>}
            {matchResult && (
              <div className="mt-4 space-y-3 border-t border-zinc-100 pt-4">
                {matchComponents.map(([key, label, scoreField]) => {
                  const score = formatComponentScore(matchResult[scoreField], matchResult.rule_version);
                  const applicable = matchResult.criteria_applicability[key];
                  const reason = detailReason(matchResult.missing_information[key]);
                  return (
                    <div key={key}>
                      <div className="flex items-start justify-between gap-3 text-xs">
                        <span className="leading-5 text-zinc-600">{label}</span>
                        <span className="shrink-0 font-semibold text-zinc-800">
                          {score ?? (applicable === false ? "Không áp dụng" : "Chưa có dữ liệu")}
                        </span>
                      </div>
                      {typeof applicable === "boolean" && (
                        <p className="mt-1 text-xs text-zinc-400">
                          {applicable ? "Tiêu chí được áp dụng" : "Tiêu chí không áp dụng"}
                        </p>
                      )}
                      {reason && <p className="mt-1 text-xs leading-5 text-amber-700">{reason}</p>}
                    </div>
                  );
                })}
                {detailReason(matchResult.missing_information.processing) && (
                  <p className="text-xs leading-5 text-amber-700">{detailReason(matchResult.missing_information.processing)}</p>
                )}
                {matchResult.matched_skills.length > 0 && <div><p className="text-xs font-medium text-emerald-700">Kỹ năng phù hợp</p><div className="mt-2 flex flex-wrap gap-1">{matchResult.matched_skills.map((skill) => <Badge key={skill} variant="success">{skill}</Badge>)}</div></div>}
                {matchResult.missing_skills.length > 0 && <div><p className="text-xs font-medium text-red-600">Kỹ năng còn thiếu</p><div className="mt-2 flex flex-wrap gap-1">{matchResult.missing_skills.map((skill) => <Badge key={skill} variant="outline">{skill}</Badge>)}</div></div>}
              </div>
            )}
          </section>

          {nextStatuses[item.status].length > 0 && <section className="rounded-xl border border-zinc-200 bg-white p-5 shadow-sm"><h2 className="font-semibold text-zinc-900">Cập nhật trạng thái</h2><p className="mt-2 text-xs leading-5 text-zinc-500">Chỉ có thể chuyển tiếp. Hệ thống sẽ gửi email thông báo sau khi cập nhật.</p><div className="mt-3 grid gap-2">{nextStatuses[item.status].map((status) => <Button key={status} type="button" variant={status === "REJECTED" ? "outline" : "default"} disabled={busy} onClick={() => setSelectedStatus(status)}>{applicationStatusLabel[status]}</Button>)}</div></section>}
        </aside>
      </div>
      {selectedStatus && <div className="fixed inset-0 z-50 flex items-end justify-center bg-zinc-950/45 p-0 sm:items-center sm:p-4" role="dialog" aria-modal="true" aria-labelledby="transition-title"><div className="w-full rounded-t-2xl bg-white p-5 shadow-2xl sm:max-w-lg sm:rounded-2xl sm:p-6"><h2 id="transition-title" className="text-lg font-semibold text-zinc-900">Xác nhận chuyển sang {applicationStatusLabel[selectedStatus]}</h2><p className="mt-2 text-sm leading-6 text-zinc-500">Thao tác này không thể hoàn tác. Trạng thái hiện tại là {applicationStatusLabel[item.status]}.</p><label className="mt-5 block text-sm font-medium text-zinc-700" htmlFor="internal-note">Ghi chú nội bộ</label><textarea id="internal-note" value={note} onChange={(event) => setNote(event.target.value)} maxLength={5000} placeholder="Chỉ Employer/Admin nhìn thấy" className="mt-2 min-h-20 w-full rounded-xl border border-zinc-300 p-3 text-sm outline-none focus:border-primary" /><label className="mt-4 block text-sm font-medium text-zinc-700" htmlFor="candidate-message">Nội dung gửi ứng viên</label><textarea id="candidate-message" value={candidateMessage} onChange={(event) => setCandidateMessage(event.target.value)} maxLength={5000} placeholder="Không bắt buộc. Email vẫn thông báo trạng thái nếu để trống." className="mt-2 min-h-24 w-full rounded-xl border border-zinc-300 p-3 text-sm outline-none focus:border-primary" /><div className="mt-5 flex justify-end gap-2"><Button type="button" variant="outline" disabled={busy} onClick={() => { setSelectedStatus(null); setNote(""); setCandidateMessage(""); }}>Hủy</Button><Button type="button" disabled={busy} onClick={() => void move()}>{busy && <Loader2 className="animate-spin" />}Xác nhận và gửi email</Button></div></div></div>}
    </div>
  );
}
