"use client";

import {
  AlertCircle,
  BriefcaseBusiness,
  Check,
  ChevronRight,
  CircleUserRound,
  FileText,
  GraduationCap,
  LoaderCircle,
  Sparkles,
  WandSparkles,
  X,
} from "lucide-react";
import Link from "next/link";
import { useState } from "react";

import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { CandidateProfileEditor } from "@/features/candidates/components/candidate-profile-editor";
import { ResumesSection } from "@/features/candidates/components/resumes-section";
import type { RunProfileMutation } from "@/features/candidates/components/profile-section";
import { cancelResumeImport } from "@/features/candidates/api";
import { useCandidateResumeImport } from "@/features/candidates/candidate-resume-import-provider";
import { useCandidateProfile } from "@/features/candidates/hooks";
import type { CandidateProfileDto } from "@/features/candidates/types";

const sectionLinks = [
  { href: "#basic-info", label: "Cá nhân", icon: CircleUserRound },
  { href: "#education", label: "Học vấn", icon: GraduationCap },
  { href: "#experience", label: "Kinh nghiệm", icon: BriefcaseBusiness },
  { href: "#skills", label: "Kỹ năng", icon: Sparkles },
  { href: "#resumes", label: "CV", icon: FileText },
];

function profileCompletion(profile: CandidateProfileDto) {
  const checks = [
    { done: Boolean(profile.full_name), label: "Thêm họ và tên" },
    { done: Boolean(profile.phone), label: "Thêm số điện thoại" },
    { done: Boolean(profile.desired_position), label: "Chọn vị trí mong muốn" },
    { done: Boolean(profile.headline), label: "Viết tiêu đề nghề nghiệp" },
    { done: Boolean(profile.summary), label: "Giới thiệu bản thân" },
    { done: profile.educations.length > 0, label: "Thêm học vấn" },
    { done: profile.experiences.length > 0, label: "Thêm kinh nghiệm hoặc dự án" },
    { done: profile.skills.length > 0, label: "Thêm kỹ năng" },
    { done: profile.resumes.some((resume) => resume.is_primary), label: "Tải lên CV chính" },
  ];
  return {
    percent: Math.round((checks.filter((item) => item.done).length / checks.length) * 100),
    missing: checks.filter((item) => !item.done),
  };
}

function formatEmbeddingTime(value: string | null) {
  if (!value) return "";
  return new Intl.DateTimeFormat("vi-VN", {
    hour: "2-digit",
    minute: "2-digit",
    day: "2-digit",
    month: "2-digit",
  }).format(new Date(value));
}

function LoadingProfile() {
  return (
    <div className="mx-auto w-full max-w-6xl animate-pulse px-4 py-8 sm:px-6">
      <div className="h-40 rounded-xl bg-zinc-100" />
      <div className="mt-6 grid gap-6 lg:grid-cols-[minmax(0,1fr)_280px]">
        <div className="space-y-5">
          {[1, 2, 3].map((item) => <div key={item} className="h-60 rounded-xl bg-zinc-100" />)}
        </div>
        <div className="h-72 rounded-xl bg-zinc-100" />
      </div>
    </div>
  );
}

export function CandidateProfilePage() {
  const { profile, setProfile, isLoading, error, setError, refresh } = useCandidateProfile();
  const { resumeImport, stalled: resumeImportStalled, pollError, retry: retryPolling, clearImport } = useCandidateResumeImport();
  const [pending, setPending] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);
  const [cancelTick, setCancelTick] = useState(0);
  const [appliedImportId, setAppliedImportId] = useState<string | null>(null);

  const appliedImport =
    appliedImportId && resumeImport?.id === appliedImportId && resumeImport.parse_status === "SUCCESS"
      ? resumeImport
      : null;

  const runMutation: RunProfileMutation = async (action, successMessage) => {
    setPending(true);
    setError(null);
    setNotice(null);
    try {
      await action();
      await refresh();
      setNotice(successMessage);
      return true;
    } catch (err) {
      setError(err instanceof Error ? err.message : "Có lỗi xảy ra. Vui lòng thử lại.");
      return false;
    } finally {
      setPending(false);
    }
  };

  if (isLoading) return <LoadingProfile />;

  if (!profile) {
    return (
      <div className="mx-auto flex min-h-[60vh] max-w-lg flex-col items-center justify-center px-4 text-center">
        <span className="flex size-12 items-center justify-center rounded-xl bg-red-50 text-red-600">
          <AlertCircle />
        </span>
        <h1 className="mt-4 text-xl font-semibold text-zinc-900">Không thể tải hồ sơ</h1>
        <p className="mt-2 text-sm text-zinc-500">{error ?? "Hồ sơ ứng viên chưa sẵn sàng."}</p>
        <Button type="button" className="mt-5" onClick={() => refresh().catch(() => undefined)}>
          Thử lại
        </Button>
      </div>
    );
  }

  const completion = profileCompletion(profile);
  const initial = profile.full_name.trim().charAt(0).toUpperCase() || "U";

  return (
    <div className="min-h-screen bg-white pb-14">
      <div className="border-b border-primary-100 bg-gradient-to-br from-primary-50/80 via-white to-accent-50/40">
        <div className="mx-auto w-full max-w-6xl px-4 py-7 sm:px-6 sm:py-10">
          <div className="flex flex-col gap-6 sm:flex-row sm:items-center sm:justify-between">
            <div className="flex min-w-0 items-center gap-4">
              <Avatar className="size-16 border-4 border-white shadow-md sm:size-20">
                {profile.avatar_url && <AvatarImage src={profile.avatar_url} alt={profile.full_name} />}
                <AvatarFallback className="text-xl sm:text-2xl">{initial}</AvatarFallback>
              </Avatar>
              <div className="min-w-0">
                <div className="flex flex-wrap items-center gap-2">
                  <h1 className="truncate text-2xl font-bold tracking-tight text-zinc-950 sm:text-3xl">
                    {profile.full_name}
                  </h1>
                  <Badge variant={profile.is_public ? "success" : "outline"}>
                    {profile.is_public ? "Đang công khai" : "Đang ẩn"}
                  </Badge>
                </div>
                <p className="mt-1.5 truncate text-sm font-medium text-primary sm:text-base">
                  {profile.headline || profile.desired_position || "Hoàn thiện tiêu đề nghề nghiệp"}
                </p>
                <p className="mt-1 truncate text-sm text-zinc-500">{profile.email}</p>
                <div className="mt-2 flex items-center gap-2 text-xs text-zinc-500">
                  <span className={`size-2 rounded-full ${profile.embedding_is_stale ? "animate-pulse bg-accent" : "bg-emerald-500"}`} />
                  {profile.embedding_is_stale
                    ? `Hồ sơ đang được đồng bộ phiên bản ${profile.profile_version}`
                    : `Hồ sơ đã sẵn sàng để matching${profile.embedding_updated_at ? ` · ${formatEmbeddingTime(profile.embedding_updated_at)}` : ""}`}
                </div>
              </div>
            </div>
            <div className="flex gap-2 sm:shrink-0">
              <Button asChild variant="outline" className="flex-1 sm:flex-none">
                <Link href="/candidate/applications">Đơn ứng tuyển</Link>
              </Button>
              <Button asChild variant="accent" className="flex-1 sm:flex-none">
                <Link href="/jobs?tab=recommended">Tìm việc phù hợp</Link>
              </Button>
            </div>
          </div>
        </div>
      </div>

      <div className="sticky top-16 z-30 border-b border-zinc-100 bg-white/95 lg:hidden">
        <nav className="mx-auto flex max-w-6xl gap-1 overflow-x-auto px-4 py-2 [scrollbar-width:none] sm:px-6">
          {sectionLinks.map((item) => (
            <a key={item.href} href={item.href} className="flex shrink-0 items-center gap-1.5 rounded-lg px-3 py-2 text-xs font-medium text-zinc-600 hover:bg-primary-50 hover:text-primary">
              <item.icon className="size-3.5" />{item.label}
            </a>
          ))}
        </nav>
      </div>

      <main className="mx-auto w-full max-w-6xl px-4 py-6 sm:px-6 sm:py-8">
        {!resumeImport && pollError && (
          <div className="mb-5 flex items-center gap-3 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
            <AlertCircle className="size-4 shrink-0" />
            <span className="flex-1">Không thể lấy lại tác vụ trích xuất CV đang chạy. Vui lòng thử lại.</span>
            <Button type="button" size="sm" variant="outline" onClick={() => retryPolling()}>
              Thử lại
            </Button>
          </div>
        )}
        {(() => {
          if (resumeImport?.parse_status !== "SUCCESS") return null;
          const applied = appliedImportId === resumeImport.id;
          return (
            <div className="mb-5 flex flex-col gap-3 rounded-xl border border-primary-200 bg-primary-50 px-4 py-3 text-sm text-primary-900 sm:flex-row sm:items-center">
              <span className="flex items-center gap-2">
                <FileText className="size-4 shrink-0 text-primary" />
                <span>
                  CV <strong>{resumeImport.original_filename}</strong> đã phân tích xong. Bấm để điền dữ liệu vào hồ sơ.
                </span>
              </span>
              <span className="flex gap-2 sm:ml-auto">
                <Button
                  type="button"
                  size="sm"
                  onClick={() => {
                    setAppliedImportId(resumeImport.id);
                    setNotice("Dữ liệu CV đã được điền vào bản nháp bên dưới. Hãy kiểm tra trước khi lưu.");
                  }}
                >
                  <WandSparkles />
                  {applied ? "Đã điền vào bản nháp" : "Điền dữ liệu từ CV"}
                </Button>
              </span>
            </div>
          );
        })()}

        {resumeImport?.parse_status === "PENDING" && (
          <div className="mb-5 flex items-center gap-3 rounded-xl border border-accent-200 bg-accent-50 px-4 py-3 text-sm text-zinc-700">
            <LoaderCircle className="size-4 shrink-0 animate-spin text-accent" />
            <span className="flex-1">
              Đang trích xuất dữ liệu từ <strong>{resumeImport.original_filename}</strong>. Bạn có thể nhập tay trong lúc chờ.
              {resumeImportStalled && " Tác vụ vẫn đang được xử lý. Bạn có thể kiểm tra lại."}
              {pollError && " Lỗi kết nối. Hãy thử kiểm tra lại."}
            </span>
            <span className="flex shrink-0 items-center gap-2">
              <Button
                type="button"
                size="sm"
                variant="outline"
                onClick={() => retryPolling()}
              >
                Kiểm tra lại
              </Button>
              <Button
                type="button"
                size="sm"
                variant="ghost"
                onClick={() => void cancelResumeImport(resumeImport.id).then(clearImport)}
              >
                Hủy
              </Button>
            </span>
          </div>
        )}
        {resumeImport?.parse_status === "FAILED" && (
          <div className="mb-5 flex items-start gap-3 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
            <AlertCircle className="mt-0.5 size-4 shrink-0" />
            <span className="flex-1">
              Phân tích CV <strong>{resumeImport.original_filename}</strong> thất bại{resumeImport.parse_error_message ? `: ${resumeImport.parse_error_message}` : ""}. Bạn có thể thử file khác hoặc nhập thủ công.
            </span>
            <span className="flex shrink-0 gap-2">
              <Button
                type="button"
                size="sm"
                variant="ghost"
                onClick={() => void cancelResumeImport(resumeImport.id).then(clearImport)}
              >
                Hủy
              </Button>
            </span>
          </div>
        )}

        {(error || notice) && (
          <div
            className={`mb-5 flex items-start gap-3 rounded-xl border px-4 py-3 text-sm ${
              error ? "border-red-200 bg-red-50 text-red-700" : "border-emerald-200 bg-emerald-50 text-emerald-700"
            }`}
          >
            {error ? <AlertCircle className="mt-0.5 size-4 shrink-0" /> : <Check className="mt-0.5 size-4 shrink-0" />}
            <span className="flex-1">{error ?? notice}</span>
            <button type="button" aria-label="Đóng thông báo" onClick={() => { setError(null); setNotice(null); }}>
              <X className="size-4" />
            </button>
          </div>
        )}

        <div className="mb-5 rounded-xl border border-zinc-200 bg-white p-4 shadow-sm lg:hidden">
          <div className="flex items-center justify-between gap-4">
            <div>
              <p className="text-sm font-semibold text-zinc-900">Hồ sơ hoàn thiện {completion.percent}%</p>
              <p className="mt-1 text-xs text-zinc-500">
                {completion.missing[0]?.label ?? "Sẵn sàng để nhà tuyển dụng tìm thấy."}
              </p>
            </div>
            <span className="text-lg font-bold text-primary">{completion.percent}%</span>
          </div>
          <div className="mt-3 h-2 overflow-hidden rounded-full bg-zinc-100">
            <div
              className="h-full rounded-full bg-gradient-to-r from-primary to-primary-400 transition-[width]"
              style={{ width: `${completion.percent}%` }}
            />
          </div>
        </div>

        <div className="grid items-start gap-6 lg:grid-cols-[minmax(0,1fr)_280px]">
          <div className="space-y-6">
            <ResumesSection
              items={profile.resumes}
              pending={pending}
              runMutation={runMutation}
              onLocalError={(message) => { setNotice(null); setError(message || null); }}
              onNotice={(message) => { setError(null); setNotice(message); }}
            />
            <CandidateProfileEditor
              key={`${profile.updated_at}:${appliedImport?.id ?? "no-import"}:${cancelTick}`}
              profile={profile}
              previewImport={appliedImport}
              onCancel={() => {
                if (appliedImport) {
                  void cancelResumeImport(appliedImport.id).then(clearImport);
                }
                setCancelTick((tick) => tick + 1);
                setAppliedImportId(null);
                setNotice(
                  appliedImport
                    ? "Đã hủy bản nháp. Dữ liệu hồ sơ trở về như trước, không có gì được lưu."
                    : "Đã hủy các thay đổi chưa được lưu.",
                );
              }}
              onSaved={(saved) => {
                setProfile(saved);
                clearImport();
                setAppliedImportId(null);
                setNotice("Hồ sơ đã được lưu từ bản nháp đã duyệt.");
              }}
            />
          </div>

          <aside className="hidden space-y-4 lg:sticky lg:top-24 lg:block">
            <div className="rounded-xl border border-zinc-200 bg-white p-5 shadow-[0_8px_28px_rgba(15,76,129,0.08)]">
              <div className="flex items-center gap-4">
                <div
                  className="grid size-16 shrink-0 place-items-center rounded-full"
                  style={{ background: `conic-gradient(#0F4C81 ${completion.percent}%, #E4E4E7 0)` }}
                >
                  <div className="grid size-12 place-items-center rounded-full bg-white text-sm font-bold text-primary">
                    {completion.percent}%
                  </div>
                </div>
                <div>
                  <h2 className="font-semibold text-zinc-900">Độ hoàn thiện</h2>
                  <p className="mt-1 text-xs leading-5 text-zinc-500">
                    Hồ sơ đầy đủ giúp tăng cơ hội được liên hệ.
                  </p>
                </div>
              </div>
              {completion.missing.length > 0 ? (
                <div className="mt-5 border-t border-zinc-100 pt-4">
                  <p className="text-xs font-semibold uppercase tracking-wide text-zinc-400">Nên bổ sung</p>
                  <ul className="mt-3 space-y-2.5">
                    {completion.missing.slice(0, 4).map((item) => (
                      <li key={item.label} className="flex items-center gap-2 text-sm text-zinc-600">
                        <span className="size-1.5 rounded-full bg-accent" />{item.label}
                      </li>
                    ))}
                  </ul>
                </div>
              ) : (
                <div className="mt-5 flex items-center gap-2 rounded-xl bg-emerald-50 p-3 text-sm font-medium text-emerald-700">
                  <Check className="size-4" />Hồ sơ đã hoàn thiện
                </div>
              )}
            </div>

            <nav className="rounded-xl border border-zinc-200 bg-white p-2 shadow-sm">
              {sectionLinks.map((item) => (
                <a key={item.href} href={item.href} className="flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium text-zinc-600 transition hover:bg-primary-50 hover:text-primary">
                  <item.icon className="size-4" />
                  <span className="flex-1">{item.label}</span>
                  <ChevronRight className="size-3.5 text-zinc-300" />
                </a>
              ))}
            </nav>
          </aside>
        </div>
      </main>
    </div>
  );
}
