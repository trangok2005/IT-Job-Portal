"use client";

import { ArrowLeft, FileUp, Loader2, Sparkles } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  createEmployerJob,
  getEmployerJob,
  getEmployerSkills,
  publishEmployerJob,
  updateEmployerJob,
} from "@/features/employer/api";
import type { JobPayload, SkillDto } from "@/features/employer/types";
import { useJDImport } from "@/features/employer/jd-import-provider";
import {
  EXPERIENCE_LABELS,
  JOB_TYPE_LABELS,
  LOCATION_OPTIONS,
  WORKPLACE_TYPE_LABELS,
} from "@/features/jobs/utils";
import type { JobDto } from "@/lib/types";

const fieldClass =
  "h-11 w-full rounded-xl border border-zinc-300 bg-white px-3.5 text-sm outline-none focus:border-primary";
const textareaClass =
  "mt-1.5 min-h-32 w-full rounded-xl border border-zinc-300 p-3.5 text-sm outline-none focus:border-primary";

export function JobForm({ jobId, importId }: { jobId?: string; importId?: string }) {
  const router = useRouter();
  const { jdImport, stalled: jdStalled, startImport, cancelImport, clearImport } = useJDImport();
  const [job, setJob] = useState<JobDto | null>(null);
  const [jdFile, setJdFile] = useState<File | null>(null);
  const [skills, setSkills] = useState<SkillDto[]>([]);
  const [selected, setSelected] = useState<string[] | null>(null);
  const [minYears, setMinYears] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(Boolean(jobId));
  const [parsing, setParsing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [submitIntent, setSubmitIntent] = useState<"draft" | "publish" | null>(null);
  const [error, setError] = useState<string | null>(null);
  const activeImport = !jobId && jdImport?.id === importId ? jdImport : null;
  const parsed = activeImport?.status === "SUCCESS" ? activeImport.parsed_data : null;
  const selectedSkills = selected ?? parsed?.required_skills ?? [];
  const isParsing = parsing || activeImport?.status === "PENDING" || activeImport?.status === "PROCESSING";

  useEffect(() => {
    const requests: [Promise<{ results: SkillDto[] }>, Promise<JobDto> | null] = [
      getEmployerSkills(),
      jobId ? getEmployerJob(jobId) : null,
    ];

    Promise.all([requests[0], requests[1]])
      .then(([skillResponse, jobResponse]) => {
        setSkills(skillResponse.results);
        if (jobResponse) {
          setJob(jobResponse);
          setSelected(jobResponse.skills.map((skill) => skill.skill));
          setMinYears(
            Object.fromEntries(
              jobResponse.skills
                .filter((s) => s.min_years !== null)
                .map((s) => [s.skill, String(s.min_years)]),
            ),
          );
        }
      })
      .catch((reason: unknown) => {
        setError(reason instanceof Error ? reason.message : "Không thể tải dữ liệu tin tuyển dụng.");
      })
      .finally(() => setLoading(false));
  }, [jobId]);

  const parseJd = async () => {
    if (!jdFile) {
      setError("Vui lòng chọn file JD PDF, DOC hoặc DOCX.");
      return;
    }
    if (jdFile.size > 5 * 1024 * 1024) {
      setError("Dung lượng JD không được vượt quá 5 MB.");
      return;
    }
    setParsing(true);
    setError(null);
    try {
      const result = await startImport(jdFile);
      router.replace(`/employer/jobs/new?import_id=${result.id}`);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Không thể đọc thông tin từ file JD.");
    } finally {
      setParsing(false);
    }
  };

  const submit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const submitter = (event.nativeEvent as SubmitEvent).submitter as HTMLButtonElement | null;
    const intent = submitter?.value === "publish" ? "publish" : "draft";
    const form = new FormData(event.currentTarget);
    const optionalNumber = (name: string) => {
      const value = String(form.get(name) ?? "");
      return value ? Number(value) : null;
    };
    const expiry = String(form.get("expires_at") ?? "");
    const payload: JobPayload = {
      title: String(form.get("title") ?? "").trim(),
      description: String(form.get("description") ?? "").trim(),
      requirements: String(form.get("requirements") ?? "").trim(),
      benefits: String(form.get("benefits") ?? "").trim(),
      location: String(form.get("location") ?? "").trim() as JobPayload["location"],
      workplace_type: String(form.get("workplace_type")) as JobPayload["workplace_type"],
      job_type: String(form.get("job_type")) as JobPayload["job_type"],
      experience_level: String(form.get("experience_level")) as JobPayload["experience_level"],
      salary_min: optionalNumber("salary_min"),
      salary_max: optionalNumber("salary_max"),
      salary_negotiable: form.get("salary_negotiable") === "on",
      expires_at: expiry ? new Date(expiry).toISOString() : null,
      required_skills: selectedSkills.map((id) => {
        const raw = minYears[id];
        const years = raw === undefined || raw.trim() === "" || Number.isNaN(Number(raw)) ? null : Number(raw);
        return { skill: id, min_years: years === null ? null : String(years), is_required: true };
      }),
      publish_immediately: !jobId && intent === "publish",
      jd_import_id: activeImport?.status === "SUCCESS" ? activeImport.id : undefined,
    };

    setSaving(true);
    setSubmitIntent(intent);
    setError(null);
    try {
      if (jobId) {
        await updateEmployerJob(jobId, payload);
        if (intent === "publish" && job?.status === "DRAFT") {
          await publishEmployerJob(jobId);
        }
      }
      else {
        await createEmployerJob(payload);
        if (payload.jd_import_id) clearImport();
      }
      router.push("/employer/jobs");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Không thể lưu tin tuyển dụng.");
    } finally {
      setSaving(false);
      setSubmitIntent(null);
    }
  };

  if (loading) {
    return <div className="mx-auto mt-8 h-72 max-w-4xl animate-pulse rounded-xl bg-zinc-100" />;
  }

  if (jobId && !job) {
    return (
      <div className="mx-auto max-w-3xl px-4 py-12 text-center">
        <p className="rounded-xl bg-red-50 p-4 text-sm text-red-700">{error ?? "Không tìm thấy tin tuyển dụng."}</p>
        <Button asChild variant="outline" className="mt-4"><Link href="/employer/jobs"><ArrowLeft />Quay lại danh sách</Link></Button>
      </div>
    );
  }

  const initial = job ?? parsed;

  return (
    <div className="mx-auto max-w-4xl px-4 py-7 sm:px-6 lg:px-8">
      <Link href="/employer/jobs" className="inline-flex items-center gap-1.5 text-sm font-medium text-zinc-500 hover:text-primary">
        <ArrowLeft className="size-4" /> Tin tuyển dụng
      </Link>
      <h1 className="mt-4 text-2xl font-bold text-zinc-900">{jobId ? "Sửa tin tuyển dụng" : "Tạo tin tuyển dụng"}</h1>
      <p className="mt-1 text-sm text-zinc-500">
        {jobId ? "Chỉnh sửa nội dung tin nháp. Tin đã đăng sẽ không thể thay đổi." : "Bạn có thể lưu nháp để hoàn thiện sau hoặc đăng tin ngay."}
      </p>
      {!jobId && (
        <section className="mt-6 rounded-xl border border-primary-100 bg-primary-50/50 p-5">
          <div className="flex items-start gap-3">
            <span className="grid size-10 shrink-0 place-items-center rounded-xl bg-primary text-white"><Sparkles className="size-5" /></span>
            <div><h2 className="font-semibold text-zinc-900">Tạo form từ file JD</h2><p className="mt-1 text-sm text-zinc-500">Gemini trích xuất nội dung để điền form. Bạn luôn là người kiểm tra và quyết định đăng tin.</p></div>
          </div>
          <div className="mt-4 flex flex-col gap-2 sm:flex-row">
            <Input
              type="file"
              accept=".pdf,.doc,.docx"
              onChange={(event) => {
                setJdFile(event.target.files?.[0] ?? null);
                setSelected(null);
              }}
              className="bg-white"
            />
            <Button type="button" variant="outline" disabled={!jdFile || isParsing} onClick={() => void parseJd()}>
              {isParsing ? <Loader2 className="animate-spin" /> : <FileUp />}
              {isParsing ? "Đang phân tích..." : "Trích xuất JD"}
            </Button>
          </div>
          {activeImport && ["PENDING", "PROCESSING"].includes(activeImport.status) && <p className="mt-3 text-sm text-primary">Bạn có thể rời trang này. Hệ thống sẽ báo trên thanh điều hướng khi JD sẵn sàng.{jdStalled && " Hệ thống đã ngừng tự động kiểm tra — tải lại trang để cập nhật trạng thái."}</p>}
          {activeImport?.status === "FAILED" && <div className="mt-3 flex items-center gap-3 text-sm text-red-700"><span>{activeImport.error_message}</span><Button type="button" variant="ghost" onClick={() => void cancelImport()}>Bỏ kết quả</Button></div>}
          {parsed && <p className="mt-3 text-sm text-emerald-700">Đã điền dữ liệu từ <strong>{activeImport?.original_filename ?? jdFile?.name}</strong>. Vui lòng kiểm tra trước khi lưu.</p>}
          {parsed && parsed.unmatched_skills.length > 0 && <p className="mt-2 text-xs text-amber-800">Skill chưa có trong taxonomy: {parsed.unmatched_skills.join(", ")}. Admin cần chuẩn hóa trước khi có thể gắn vào tin.</p>}
        </section>
      )}
      {error && <p className="mt-5 rounded-xl bg-red-50 p-4 text-sm text-red-700">{error}</p>}

      <form key={activeImport?.updated_at ?? "manual"} onSubmit={submit} className="mt-6 space-y-6 rounded-xl border border-zinc-200 bg-white p-5 shadow-sm sm:p-7">
        <label className="block text-sm font-medium text-zinc-700">
          Tiêu đề <span className="text-red-500">*</span>
          <Input name="title" defaultValue={initial?.title ?? ""} className="mt-1.5" required />
        </label>

        <div className="grid gap-4 sm:grid-cols-2">
          <Field label="Địa điểm">
            <select name="location" defaultValue={initial?.location ?? ""} className={fieldClass}>
              <option value="">Chọn địa điểm</option>
              {LOCATION_OPTIONS.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}
            </select>
          </Field>
          <Field label="Hạn nhận hồ sơ"><Input name="expires_at" type="datetime-local" defaultValue={initial?.expires_at?.slice(0, 16) ?? ""} /></Field>
          <Field label="Nơi làm việc">
            <select name="workplace_type" defaultValue={initial?.workplace_type ?? "ONSITE"} className={fieldClass}>
              {Object.entries(WORKPLACE_TYPE_LABELS).map(([value, label]) => <option key={value} value={value}>{label}</option>)}
            </select>
          </Field>
          <Field label="Loại việc">
            <select name="job_type" defaultValue={initial?.job_type ?? "FULL_TIME"} className={fieldClass}>
              {Object.entries(JOB_TYPE_LABELS).map(([value, label]) => <option key={value} value={value}>{label}</option>)}
            </select>
          </Field>
          <Field label="Cấp độ">
            <select name="experience_level" defaultValue={initial?.experience_level ?? ""} className={fieldClass}>
              <option value="">Không yêu cầu</option>{Object.entries(EXPERIENCE_LABELS).map(([value, label]) => <option key={value} value={value}>{label}</option>)}
            </select>
          </Field>
          <Field label="Lương tối thiểu"><Input name="salary_min" type="number" min="0" defaultValue={initial?.salary_min ?? ""} /></Field>
          <Field label="Lương tối đa"><Input name="salary_max" type="number" min="0" defaultValue={initial?.salary_max ?? ""} /></Field>
        </div>

        <label className="flex items-center gap-2 text-sm text-zinc-600">
          <input name="salary_negotiable" type="checkbox" defaultChecked={initial?.salary_negotiable ?? false} className="size-4 accent-primary" /> Lương thỏa thuận
        </label>

        <label className="block text-sm font-medium text-zinc-700">Mô tả công việc <span className="text-red-500">*</span><textarea name="description" defaultValue={initial?.description ?? ""} className={textareaClass} required /></label>
        <label className="block text-sm font-medium text-zinc-700">Yêu cầu ứng viên<textarea name="requirements" defaultValue={initial?.requirements ?? ""} className={textareaClass} /></label>
        <label className="block text-sm font-medium text-zinc-700">Quyền lợi<textarea name="benefits" defaultValue={initial?.benefits ?? ""} className={textareaClass} /></label>

        <fieldset>
          <legend className="text-sm font-medium text-zinc-700">Kỹ năng yêu cầu</legend>
          <p className="mt-1 text-xs text-zinc-400">Tùy chọn: nhập số năm kinh nghiệm tối thiểu cho từng kỹ năng.</p>
          <div className="mt-2 flex max-h-56 flex-wrap gap-2 overflow-y-auto rounded-xl border border-zinc-200 p-3">
            {skills.map((skill) => {
              const checked = selectedSkills.includes(skill.id);
              return (
                <label key={skill.id} className={`cursor-pointer rounded-full border px-3 py-1.5 text-xs font-medium ${checked ? "border-primary bg-primary text-white" : "border-zinc-200 text-zinc-600"}`}>
                  <input type="checkbox" className="sr-only" checked={checked} onChange={() => setSelected((current) => { const values = current ?? selectedSkills; return checked ? values.filter((id) => id !== skill.id) : [...values, skill.id]; })} />
                  {skill.name}
                </label>
              );
            })}
          </div>
          {selectedSkills.length > 0 && (
            <div className="mt-3 space-y-2">
              {selectedSkills.map((id) => {
                const skill = skills.find((s) => s.id === id);
                if (!skill) return null;
                return (
                  <div key={id} className="flex items-center gap-2">
                    <span className="w-44 shrink-0 truncate text-sm text-zinc-700">{skill.name}</span>
                    <input
                      type="number"
                      min="0"
                      step="0.5"
                      placeholder="Số năm tối thiểu"
                      value={minYears[id] ?? ""}
                      onChange={(e) => setMinYears((current) => ({ ...current, [id]: e.target.value }))}
                      className={`${fieldClass} mt-0 h-9 w-40`}
                    />
                    <span className="text-xs text-zinc-400">năm</span>
                  </div>
                );
              })}
            </div>
          )}
        </fieldset>

        <div className="flex justify-end gap-2 border-t border-zinc-100 pt-5">
          <Button asChild type="button" variant="ghost"><Link href="/employer/jobs">Hủy</Link></Button>
          <Button type="submit" name="intent" value="draft" variant="outline" disabled={saving}>
            {saving && submitIntent === "draft" && <Loader2 className="animate-spin" />}
            {saving && submitIntent === "draft" ? "Đang lưu..." : jobId ? "Lưu thay đổi" : "Lưu nháp"}
          </Button>
          {(!jobId || job?.status === "DRAFT") && (
            <Button type="submit" name="intent" value="publish" variant="accent" disabled={saving}>
              {saving && submitIntent === "publish" && <Loader2 className="animate-spin" />}
              {saving && submitIntent === "publish" ? "Đang đăng..." : "Đăng tin ngay"}
            </Button>
          )}
        </div>
      </form>
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return <label className="block text-sm font-medium text-zinc-700">{label}<div className="mt-1.5">{children}</div></label>;
}
