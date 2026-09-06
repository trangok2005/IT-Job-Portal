"use client";

import { AlertCircle, ArrowLeft, CircleCheck, FileUp, Loader2, Plus, Sparkles, Trash2 } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import {
  createEmployerJob,
  getEmployerJob,
  getEmployerSkills,
  getMyCompany,
  publishEmployerJob,
  updateEmployerJob,
} from "@/features/employer/api";
import { JOB_STATUS_LABELS, type CompanyStatus, type JobPayload, type RequiredEducationLevel, type SkillDto } from "@/features/employer/types";
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
type SkillSpec = NonNullable<JobPayload["required_skills"]>[number];

const educationLevelLabels: Record<RequiredEducationLevel, string> = {
  NONE: "Không yêu cầu bằng cấp",
  ASSOCIATE: "Cao đẳng",
  BACHELOR: "Cử nhân / Kỹ sư",
  MASTER: "Thạc sĩ",
  PHD: "Tiến sĩ",
};

function getEducationLevel(value: object | null): RequiredEducationLevel | null {
  if (!value || !("required_education_level" in value)) return null;
  const level = value.required_education_level;
  return typeof level === "string" && level in educationLevelLabels
    ? level as RequiredEducationLevel
    : null;
}

function toDateTimeLocal(value: string | null | undefined) {
  if (!value) return "";
  const date = new Date(value);
  const pad = (part: number) => String(part).padStart(2, "0");
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`;
}

export function JobForm({ jobId, importId }: { jobId?: string; importId?: string }) {
  const router = useRouter();
  const { jdImport, stalled: jdStalled, pollError, retry: retryPolling, startImport, cancelImport, clearImport } = useJDImport();
  const [job, setJob] = useState<JobDto | null>(null);
  const [companyStatus, setCompanyStatus] = useState<CompanyStatus | null>(null);
  const [jdFile, setJdFile] = useState<File | null>(null);
  const [skills, setSkills] = useState<SkillDto[]>([]);
  const [skillSpecs, setSkillSpecs] = useState<SkillSpec[] | null>(null);
  const [skillToAdd, setSkillToAdd] = useState("");
  const [loading, setLoading] = useState(Boolean(jobId));
  const [parsing, setParsing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [submitIntent, setSubmitIntent] = useState<"draft" | "publish" | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [jdApplied, setJdApplied] = useState(false);
  const activeImport = !jobId && jdImport?.id === importId ? jdImport : null;
  const parsed = jdApplied && activeImport?.status === "SUCCESS" ? activeImport.parsed_data : null;
  const selectedSkills = skillSpecs ?? parsed?.resolved_skills.map((skill) => ({
    skill: skill.id,
    is_required: skill.is_required,
  })) ?? [];
  const availableSkills = skills.filter(
    (skill) => !selectedSkills.some((selectedSkill) => selectedSkill.skill === skill.id),
  );
  const isParsing = parsing || activeImport?.status === "PENDING" || activeImport?.status === "PROCESSING";

  useEffect(() => {
    Promise.all([
      getEmployerSkills(),
      jobId ? getEmployerJob(jobId) : Promise.resolve(null),
      getMyCompany(),
    ])
      .then(([skillResponse, jobResponse, company]) => {
        setSkills(skillResponse.results);
        setCompanyStatus(company.status);
        if (jobResponse) {
          setJob(jobResponse);
          setSkillSpecs(
            jobResponse.skills.map((skill) => ({
              skill: skill.skill,
              is_required: skill.is_required,
            })),
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
      setJdApplied(false);
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
    const educationLevel = String(form.get("required_education_level") ?? "");
    const payload: JobPayload = {
      title: String(form.get("title") ?? "").trim(),
      description: String(form.get("description") ?? "").trim(),
      requirements: String(form.get("requirements") ?? "").trim(),
      benefits: String(form.get("benefits") ?? "").trim(),
      location: String(form.get("location") ?? "").trim() as JobPayload["location"],
      workplace_type: String(form.get("workplace_type")) as JobPayload["workplace_type"],
      job_type: String(form.get("job_type")) as JobPayload["job_type"],
      experience_level: String(form.get("experience_level")) as JobPayload["experience_level"],
      required_education_level: educationLevel
        ? educationLevel as RequiredEducationLevel
        : null,
      salary_min: optionalNumber("salary_min"),
      salary_max: optionalNumber("salary_max"),
      salary_negotiable: form.get("salary_negotiable") === "on",
      expires_at: expiry ? new Date(expiry).toISOString() : null,
      required_skills: selectedSkills,
      publish_immediately: !jobId && intent === "publish",
      jd_import_id: jdApplied && activeImport?.status === "SUCCESS" ? activeImport.id : undefined,
    };

    if (typeof payload.salary_min === "number" && typeof payload.salary_max === "number" && payload.salary_min > payload.salary_max) {
      setError("Lương tối thiểu không được lớn hơn lương tối đa.");
      return;
    }
    if (payload.expires_at && new Date(payload.expires_at).getTime() <= Date.now()) {
      setError("Hạn nhận hồ sơ phải ở tương lai.");
      return;
    }

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

  if (jobId && job && job.status !== "DRAFT") {
    return (
      <div className="mx-auto max-w-3xl px-4 py-12 text-center">
        <p className="rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-800">
          Chỉ tin nháp mới có thể chỉnh sửa. Tin này đang ở trạng thái {JOB_STATUS_LABELS[job.status]}.
        </p>
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
          {!jdImport && pollError && (
            <div className="mb-4 flex items-center gap-3 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
              <AlertCircle className="size-4 shrink-0" />
              <span className="flex-1">Không thể lấy lại tác vụ trích xuất JD đang chạy. Vui lòng thử lại.</span>
              <Button type="button" size="sm" variant="outline" onClick={() => retryPolling()}>
                Thử lại
              </Button>
            </div>
          )}
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
                setSkillSpecs(null);
                setSkillToAdd("");
              }}
              className="bg-white"
            />
            <Button type="button" variant="outline" disabled={!jdFile || isParsing} onClick={() => void parseJd()}>
              {isParsing ? <Loader2 className="animate-spin" /> : <FileUp />}
              {isParsing ? "Đang phân tích..." : "Trích xuất JD"}
            </Button>
          </div>
          {activeImport && ["PENDING", "PROCESSING"].includes(activeImport.status) && (
            <div className="mt-3 flex items-center gap-3 text-sm text-primary">
              <Loader2 className="size-4 shrink-0 animate-spin" />
              <span className="flex-1">
                Đang trích xuất dữ liệu từ file JD. Bạn có thể rời trang này.
                {jdStalled && " Tác vụ vẫn đang được xử lý. Bạn có thể kiểm tra lại."}
                {pollError && " Lỗi kết nối. Hãy thử kiểm tra lại."}
              </span>
              <Button type="button" size="sm" variant="outline" onClick={() => retryPolling()}>
                Kiểm tra lại
              </Button>
            </div>
          )}
          {activeImport?.status === "FAILED" && (
            <div className="mt-3 flex items-center gap-3 text-sm text-red-700">
              <AlertCircle className="size-4 shrink-0" />
              <span className="flex-1">{activeImport.error_message}</span>
              <Button type="button" variant="ghost" onClick={() => void cancelImport()}>Hủy</Button>
            </div>
          )}
          {activeImport?.status === "SUCCESS" && (
            <div className="mt-3 flex items-center gap-3 text-sm text-emerald-700">
              <CircleCheck className="size-4 shrink-0" />
              <span className="flex-1">Đã trích xuất xong từ <strong>{activeImport.original_filename}</strong>.</span>
              {!jdApplied && (
                <Button type="button" size="sm" onClick={() => {
                  setJdApplied(true);
                }}>
                  <Sparkles /> Áp dụng vào biểu mẫu
                </Button>
              )}
              {jdApplied && <span className="text-xs text-zinc-400">Đã áp dụng</span>}
            </div>
          )}
          {parsed && parsed.unmatched_skills.length > 0 && <p className="mt-2 text-xs text-amber-800">Skill chưa có trong taxonomy: {parsed.unmatched_skills.join(", ")}. Admin cần chuẩn hóa trước khi có thể gắn vào tin.</p>}
        </section>
      )}
      {error && <p className="mt-5 rounded-xl bg-red-50 p-4 text-sm text-red-700">{error}</p>}

      <form key={`${activeImport?.updated_at ?? "manual"}:${jdApplied}`} onSubmit={submit} className="mt-6 space-y-6 rounded-xl border border-zinc-200 bg-white p-5 shadow-sm sm:p-7">
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
          <Field label="Hạn nhận hồ sơ"><Input name="expires_at" type="datetime-local" defaultValue={toDateTimeLocal(initial?.expires_at)} /></Field>
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
          <Field label="Yêu cầu học vấn">
            <select
              name="required_education_level"
              defaultValue={getEducationLevel(initial) ?? ""}
              className={fieldClass}
            >
              <option value="">Không nêu yêu cầu</option>
              {Object.entries(educationLevelLabels).map(([value, label]) => (
                <option key={value} value={value}>{label}</option>
              ))}
            </select>
            <span className="mt-1 block text-xs font-normal text-zinc-500">
              “Không nêu yêu cầu” khác với xác nhận rõ rằng công việc không yêu cầu bằng cấp.
            </span>
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
          <legend className="text-sm font-medium text-zinc-700">Kỹ năng</legend>
          <p className="mt-1 text-xs text-zinc-500">
            Đánh dấu “Bắt buộc” cho kỹ năng ứng viên cần có. Bỏ chọn nếu kỹ năng chỉ là ưu tiên.
          </p>
          <div className="mt-3 flex flex-col gap-2 sm:flex-row">
            <select
              value={skillToAdd}
              onChange={(event) => setSkillToAdd(event.target.value)}
              className={fieldClass}
              aria-label="Chọn kỹ năng để thêm"
            >
              <option value="">Chọn kỹ năng</option>
              {availableSkills.map((skill) => (
                <option key={skill.id} value={skill.id}>{skill.name}</option>
              ))}
            </select>
            <Button
              type="button"
              variant="outline"
              disabled={!skillToAdd}
              onClick={() => {
                setSkillSpecs((current) => [
                  ...(current ?? selectedSkills),
                  { skill: skillToAdd, is_required: true },
                ]);
                setSkillToAdd("");
              }}
              className="shrink-0"
            >
              <Plus /> Thêm kỹ năng
            </Button>
          </div>
          <div className="mt-3 space-y-2">
            {selectedSkills.length === 0 && (
              <p className="rounded-xl border border-dashed border-zinc-300 px-4 py-5 text-center text-sm text-zinc-500">
                Chưa có kỹ năng nào được thêm.
              </p>
            )}
            {selectedSkills.map((skillSpec) => {
              const skillName = skills.find((skill) => skill.id === skillSpec.skill)?.name
                ?? job?.skills.find((skill) => skill.skill === skillSpec.skill)?.skill_name
                ?? parsed?.resolved_skills.find((skill) => skill.id === skillSpec.skill)?.name
                ?? "Kỹ năng không xác định";
              const parsedSkill = parsed?.resolved_skills.find((skill) => skill.id === skillSpec.skill);
              const checkboxId = `skill-required-${skillSpec.skill}`;

              return (
                <div
                  key={skillSpec.skill}
                  className="flex flex-col gap-3 rounded-xl border border-zinc-200 bg-zinc-50/60 px-3.5 py-3 sm:flex-row sm:items-center"
                >
                  <span className="min-w-0 flex-1 truncate text-sm font-medium text-zinc-800">
                    {skillName}
                    {parsedSkill?.status === "PENDING" && <span className="ml-2 rounded-full bg-amber-100 px-2 py-0.5 text-[11px] font-medium text-amber-800">Chờ duyệt</span>}
                  </span>
                  <div className="flex items-center justify-between gap-4 sm:justify-end">
                    <label htmlFor={checkboxId} className="flex cursor-pointer items-center gap-2 text-sm text-zinc-700">
                      <Checkbox
                        id={checkboxId}
                        checked={skillSpec.is_required}
                        onCheckedChange={(checked) => setSkillSpecs((current) =>
                          (current ?? selectedSkills).map((item) =>
                            item.skill === skillSpec.skill
                              ? { ...item, is_required: checked === true }
                              : item,
                          )
                        )}
                      />
                      Bắt buộc
                    </label>
                    <Button
                      type="button"
                      variant="ghost"
                      size="icon"
                      onClick={() => setSkillSpecs((current) =>
                        (current ?? selectedSkills).filter((item) => item.skill !== skillSpec.skill)
                      )}
                      aria-label={`Xóa kỹ năng ${skillName}`}
                      title={`Xóa ${skillName}`}
                      className="text-zinc-500 hover:text-red-600"
                    >
                      <Trash2 />
                    </Button>
                  </div>
                </div>
              );
            })}
          </div>
        </fieldset>

        <div className="flex flex-col-reverse gap-2 border-t border-zinc-100 pt-5 sm:flex-row sm:justify-end">
          <Button asChild type="button" variant="ghost" className="w-full sm:w-auto"><Link href="/employer/jobs">Hủy</Link></Button>
          <Button type="submit" name="intent" value="draft" variant="outline" disabled={saving} className="w-full sm:w-auto">
            {saving && submitIntent === "draft" && <Loader2 className="animate-spin" />}
            {saving && submitIntent === "draft" ? "Đang lưu..." : jobId ? "Lưu thay đổi" : "Lưu nháp"}
          </Button>
          {companyStatus === "APPROVED" && (!jobId || job?.status === "DRAFT") && (
            <Button type="submit" name="intent" value="publish" variant="accent" disabled={saving} className="w-full sm:w-auto">
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
