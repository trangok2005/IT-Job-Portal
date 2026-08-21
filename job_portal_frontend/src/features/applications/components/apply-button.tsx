"use client";

import { CheckCircle2, Loader2, Send, X } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { applyToJob } from "@/features/applications/api";
import { consumePendingApplication, rememberPendingApplication } from "@/lib/auth";
import { useAuth } from "@/lib/auth-provider";

export function ApplyButton({ jobId }: { jobId: string }) {
  const { user } = useAuth();
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [coverLetter, setCoverLetter] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [applicationId, setApplicationId] = useState<string | null>(null);

  useEffect(() => {
    if (user?.role !== "CANDIDATE" || !consumePendingApplication(jobId)) return;
    queueMicrotask(() => {
      setActionError(null);
      setOpen(true);
    });
  }, [jobId, user]);

  useEffect(() => {
    if (!open) return;
    const close = (event: KeyboardEvent) => { if (event.key === "Escape") setOpen(false); };
    window.addEventListener("keydown", close);
    return () => window.removeEventListener("keydown", close);
  }, [open]);

  const startApply = () => {
    if (!user) {
      rememberPendingApplication(jobId);
      const redirectTo = encodeURIComponent(`/jobs/${jobId}`);
      router.push(`/login?redirect_to=${redirectTo}`);
      return;
    }
    if (user.role !== "CANDIDATE") {
      setActionError("Chỉ tài khoản ứng viên mới có thể ứng tuyển việc làm.");
      return;
    }
    setActionError(null);
    setError(null);
    setOpen(true);
  };

  const submit = async () => {
    setSubmitting(true);
    setError(null);
    try {
      const application = await applyToJob(jobId, coverLetter);
      setApplicationId(application.id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Không thể gửi hồ sơ ứng tuyển.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <>
      <Button type="button" variant="accent" size="lg" className="w-full sm:w-auto" onClick={startApply}>
        <Send />Ứng tuyển ngay
      </Button>
      {actionError && (
        <p role="alert" className="mt-3 rounded-xl bg-red-50 px-4 py-3 text-sm text-red-600">
          {actionError}
        </p>
      )}
      {open && (
        <div className="fixed inset-0 z-50 grid place-items-end bg-zinc-950/45 p-0 sm:place-items-center sm:p-4" role="dialog" aria-modal="true" aria-label="Xác nhận ứng tuyển">
          <div className="max-h-[92vh] w-full overflow-y-auto rounded-t-2xl bg-white p-5 shadow-2xl sm:max-w-lg sm:rounded-xl sm:p-6">
            <div className="flex items-start justify-between gap-4">
              <div>
                <h2 className="text-xl font-bold text-zinc-900">Xác nhận ứng tuyển</h2>
                <p className="mt-1 text-sm text-zinc-500">Hệ thống dùng CV chính trong hồ sơ của bạn.</p>
              </div>
              <button type="button" onClick={() => setOpen(false)} className="rounded-lg p-2 text-zinc-400 hover:bg-zinc-100"><X className="size-5" /></button>
            </div>
            {applicationId ? (
              <div className="mt-6 text-center">
                <CheckCircle2 className="mx-auto size-12 text-emerald-600" />
                <p className="mt-3 font-semibold text-zinc-900">Hồ sơ đã được gửi</p>
                <p className="mt-1 text-sm text-zinc-500">Bạn có thể theo dõi trạng thái trong danh sách đơn ứng tuyển.</p>
                <Button asChild className="mt-5 w-full"><Link href={`/candidate/applications/${applicationId}`}>Xem đơn ứng tuyển</Link></Button>
              </div>
            ) : (
              <>
                <label htmlFor="cover-letter" className="mt-6 block text-sm font-medium text-zinc-700">Thư giới thiệu <span className="font-normal text-zinc-400">(không bắt buộc)</span></label>
                <textarea id="cover-letter" value={coverLetter} onChange={(event) => setCoverLetter(event.target.value)} className="mt-2 min-h-36 w-full rounded-xl border border-zinc-300 p-3.5 text-sm outline-none focus:border-primary focus:ring-2 focus:ring-primary/20" placeholder="Chia sẻ ngắn gọn vì sao bạn phù hợp với vị trí..." />
                {error && <p className="mt-3 rounded-xl bg-red-50 px-4 py-3 text-sm text-red-600">{error}</p>}
                <div className="mt-5 flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
                  <Button type="button" variant="ghost" onClick={() => setOpen(false)}>Hủy</Button>
                  <Button type="button" variant="accent" onClick={submit} disabled={submitting}>
                    {submitting ? <Loader2 className="animate-spin" /> : <Send />}Gửi hồ sơ
                  </Button>
                </div>
              </>
            )}
          </div>
        </div>
      )}
    </>
  );
}
