"use client";

import {
  AlertCircle,
  CheckCircle2,
  Download,
  FileText,
  LoaderCircle,
  Star,
  Trash2,
  UploadCloud,
} from "lucide-react";
import { useRef } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { deleteResume, setPrimaryResume } from "@/features/candidates/api";
import { useCandidateResumeImport } from "@/features/candidates/candidate-resume-import-provider";
import type { ResumeDto } from "@/features/candidates/types";
import {
  EmptySection,
  ProfileSection,
  type RunProfileMutation,
} from "@/features/candidates/components/profile-section";

const statusLabels: Record<ResumeDto["parse_status"], string> = {
  PENDING: "Đang phân tích",
  SUCCESS: "Đã phân tích",
  FAILED: "Phân tích lỗi",
  SKIPPED: "Chưa phân tích",
};

function formatSize(bytes: number | null) {
  if (!bytes) return "Không rõ dung lượng";
  if (bytes < 1024 * 1024) return `${Math.ceil(bytes / 1024)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function StatusIcon({ status }: { status: ResumeDto["parse_status"] }) {
  if (status === "SUCCESS") return <CheckCircle2 className="size-4 text-emerald-600" />;
  if (status === "FAILED") return <AlertCircle className="size-4 text-red-500" />;
  if (status === "PENDING") return <LoaderCircle className="size-4 animate-spin text-accent" />;
  return <FileText className="size-4 text-zinc-400" />;
}

export function ResumesSection({
  items,
  pending,
  runMutation,
  onLocalError,
  onNotice,
}: {
  items: ResumeDto[];
  pending: boolean;
  runMutation: RunProfileMutation;
  onLocalError: (message: string) => void;
  onNotice?: (message: string) => void;
}) {
  const fileInput = useRef<HTMLInputElement>(null);
  const { startImport } = useCandidateResumeImport();

  const chooseFile = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file) return;
    const extension = file.name.split(".").pop()?.toLowerCase();
    if (!extension || !["pdf", "doc", "docx"].includes(extension)) {
      onLocalError("CV chỉ hỗ trợ file PDF, DOC hoặc DOCX.");
      return;
    }
    if (file.size > 5 * 1024 * 1024) {
      onLocalError("Dung lượng CV không được vượt quá 5 MB.");
      return;
    }
    try {
      await startImport(file);
      onLocalError("");
      onNotice?.("CV đã được tải lên. AI đang phân tích — theo dõi trạng thái ở thanh trên cùng.");
    } catch (err) {
      onLocalError(err instanceof Error ? err.message : "Không thể tải CV lên. Vui lòng thử lại.");
    }
  };

  const remove = async (resume: ResumeDto) => {
    if (!window.confirm(`Xóa CV ${resume.original_filename}?`)) return;
    await runMutation(() => deleteResume(resume.id), "Đã xóa CV.");
  };

  return (
    <ProfileSection
      id="resumes"
      icon={FileText}
      title="CV của bạn"
      description="CV chính sẽ được dùng khi ứng tuyển và hỗ trợ AI matching."
      action={
        <>
          <input
            ref={fileInput}
            type="file"
            accept=".pdf,.doc,.docx"
            className="hidden"
            onChange={chooseFile}
          />
          <Button type="button" variant="accent" size="sm" disabled={pending} onClick={() => fileInput.current?.click()}>
            <UploadCloud />
            <span className="hidden sm:inline">Tải CV</span>
          </Button>
        </>
      }
    >
      <button
        type="button"
        onClick={() => fileInput.current?.click()}
        disabled={pending}
        className="mb-5 flex w-full flex-col items-center rounded-xl border border-dashed border-primary-200 bg-primary-50/40 px-4 py-6 text-center transition hover:border-primary hover:bg-primary-50 disabled:opacity-60"
      >
        <span className="flex size-11 items-center justify-center rounded-xl bg-white text-primary shadow-sm">
          <UploadCloud className="size-5" />
        </span>
        <span className="mt-3 text-sm font-semibold text-primary">Chọn CV từ thiết bị</span>
        <span className="mt-1 text-xs text-zinc-500">PDF, DOC, DOCX · Tối đa 10 MB</span>
      </button>

      {!items.length ? (
        <EmptySection>Bạn cần ít nhất một CV chính trước khi ứng tuyển.</EmptySection>
      ) : (
        <div className="space-y-3">
          {items.map((resume) => (
            <div
              key={resume.id}
              className="flex flex-col gap-3 rounded-xl border border-zinc-200 p-4 sm:flex-row sm:items-center"
            >
              <span className="flex size-11 shrink-0 items-center justify-center rounded-xl bg-red-50 text-red-600">
                <FileText className="size-5" />
              </span>
              <div className="min-w-0 flex-1">
                <div className="flex flex-wrap items-center gap-2">
                  <p className="max-w-full truncate text-sm font-semibold text-zinc-900">{resume.original_filename}</p>
                  {resume.is_primary && <Badge variant="accent"><Star className="mr-1 size-3" />CV chính</Badge>}
                </div>
                <div className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-zinc-500">
                  <span>{formatSize(resume.file_size_bytes)}</span>
                  <span className="inline-flex items-center gap-1">
                    <StatusIcon status={resume.parse_status} />
                    {statusLabels[resume.parse_status]}
                  </span>
                </div>
              </div>
              <div className="flex flex-wrap items-center gap-1 border-t border-zinc-100 pt-3 sm:border-0 sm:pt-0">
                <Button asChild type="button" variant="ghost" size="sm">
                  <a href={resume.file_url} target="_blank" rel="noreferrer"><Download />Xem</a>
                </Button>
                {!resume.is_primary && (
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    disabled={pending}
                    onClick={() => runMutation(() => setPrimaryResume(resume.id), "Đã đặt CV chính.")}
                  >
                    <Star />Đặt chính
                  </Button>
                )}
                <Button
                  type="button"
                  variant="ghost"
                  size="icon"
                  disabled={pending}
                  className="ml-auto text-red-500 hover:bg-red-50 hover:text-red-600 sm:ml-0"
                  aria-label="Xóa CV"
                  onClick={() => remove(resume)}
                >
                  <Trash2 />
                </Button>
              </div>
            </div>
          ))}
        </div>
      )}
    </ProfileSection>
  );
}
