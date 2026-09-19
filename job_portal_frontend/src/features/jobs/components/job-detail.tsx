import {
  BarChart3,
  BriefcaseBusiness,
  Building2,
  GraduationCap,
  MapPin,
  TrendingUp,
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { ApplyButton } from "@/features/applications/components/apply-button";
import {
  EXPERIENCE_LABELS,
  formatSalary,
  JOB_TYPE_LABELS,
  WORKPLACE_TYPE_LABELS,
} from "@/features/jobs/utils";
import type { JobDto } from "@/lib/types";

const EDUCATION_LABELS = {
  NONE: "Không yêu cầu bằng cấp",
  ASSOCIATE: "Cao đẳng",
  BACHELOR: "Cử nhân / Kỹ sư",
  MASTER: "Thạc sĩ",
  PHD: "Tiến sĩ",
} as const;

export function JobDetail({ job, headingLevel = "h2" }: { job: JobDto; headingLevel?: "h1" | "h2" }) {
  const requiredSkills = job.skills.filter((skill) => skill.is_required);
  const preferredSkills = job.skills.filter((skill) => !skill.is_required);
  const Title = headingLevel;
  const hasContent = Boolean(job.description || job.requirements || job.benefits);

  return (
    <div className="flex min-w-0 flex-col gap-4 lg:grid lg:grid-cols-[minmax(0,1fr)_340px] lg:items-start lg:gap-6">
      <div className="contents lg:block lg:space-y-6">
        <section className="order-1 min-w-0 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm md:p-6 lg:p-8">
          <div className="flex min-w-0 items-start gap-3 sm:gap-4">
            <span
              className="flex size-12 shrink-0 items-center justify-center rounded-xl bg-primary-50 text-lg font-bold text-primary ring-1 ring-primary/10 md:size-14 md:rounded-2xl md:text-xl lg:size-16 lg:text-2xl"
              aria-hidden="true"
            >
              {job.company_name.charAt(0).toUpperCase()}
            </span>
            <div className="min-w-0 flex-1">
              <Title className="break-words text-2xl leading-[1.2] font-bold tracking-tight text-slate-900 md:text-3xl lg:text-[2rem]">
                {job.title}
              </Title>
              <p className="mt-1.5 break-words text-sm font-medium text-slate-500 md:text-base">{job.company_name}</p>
            </div>
          </div>

          <dl className="mt-5 grid grid-cols-1 gap-x-4 gap-y-4 border-t border-slate-100 pt-5 min-[360px]:grid-cols-2 md:mt-6 md:gap-x-6 md:pt-6">
            {job.location && (
              <div className="flex min-w-0 gap-3">
                <MapPin className="mt-0.5 size-5 shrink-0 text-primary" aria-hidden="true" />
                <div className="min-w-0">
                  <dt className="text-xs font-medium text-slate-400">Địa điểm</dt>
                  <dd className="mt-1 break-words text-sm font-medium text-slate-700">{job.location}</dd>
                </div>
              </div>
            )}
            <div className="flex min-w-0 gap-3">
              <BriefcaseBusiness className="mt-0.5 size-5 shrink-0 text-primary" aria-hidden="true" />
              <div className="min-w-0">
                <dt className="text-xs font-medium text-slate-400">Hình thức</dt>
                <dd className="mt-1 break-words text-sm font-medium text-slate-700">
                  {JOB_TYPE_LABELS[job.job_type] ?? job.job_type}
                </dd>
              </div>
            </div>
            <div className="flex min-w-0 gap-3">
              <Building2 className="mt-0.5 size-5 shrink-0 text-primary" aria-hidden="true" />
              <div className="min-w-0">
                <dt className="text-xs font-medium text-slate-400">Nơi làm việc</dt>
                <dd className="mt-1 break-words text-sm font-medium text-slate-700">
                  {WORKPLACE_TYPE_LABELS[job.workplace_type] ?? job.workplace_type}
                </dd>
              </div>
            </div>
            {job.experience_level && (
              <div className="flex min-w-0 gap-3">
                <BarChart3 className="mt-0.5 size-5 shrink-0 text-primary" aria-hidden="true" />
                <div className="min-w-0">
                  <dt className="text-xs font-medium text-slate-400">Kinh nghiệm</dt>
                  <dd className="mt-1 break-words text-sm font-medium text-slate-700">
                    {EXPERIENCE_LABELS[job.experience_level] ?? job.experience_level}
                  </dd>
                </div>
              </div>
            )}
            {job.required_education_level && (
              <div className="flex min-w-0 gap-3">
                <GraduationCap className="mt-0.5 size-5 shrink-0 text-primary" aria-hidden="true" />
                <div className="min-w-0">
                  <dt className="text-xs font-medium text-slate-400">Học vấn</dt>
                  <dd className="mt-1 break-words text-sm font-medium text-slate-700">
                    {EDUCATION_LABELS[job.required_education_level]}
                  </dd>
                </div>
              </div>
            )}
          </dl>
        </section>

        {job.skills.length > 0 && (
          <section className="order-2 min-w-0 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm md:p-6 lg:p-8" aria-labelledby="job-skills-heading">
            <h2 id="job-skills-heading" className="text-xl font-semibold text-slate-900">Kỹ năng</h2>
            <div className="mt-4 space-y-4">
              {requiredSkills.length > 0 && (
                <div>
                  <h3 className="text-sm font-semibold text-slate-700">Kỹ năng yêu cầu</h3>
                  <div className="mt-3 flex flex-wrap gap-2">
                    {requiredSkills.map((skill) => (
                      <Badge key={skill.id} className="max-w-full whitespace-normal px-3 py-1.5 text-left text-xs leading-5 break-words sm:text-sm">
                        {skill.skill_name}
                      </Badge>
                    ))}
                  </div>
                </div>
              )}
              {preferredSkills.length > 0 && (
                <div>
                  <h3 className="text-sm font-semibold text-slate-700">Kỹ năng ưu tiên</h3>
                  <div className="mt-3 flex flex-wrap gap-2">
                    {preferredSkills.map((skill) => (
                      <Badge key={skill.id} variant="outline" className="max-w-full whitespace-normal bg-white px-3 py-1.5 text-left text-xs leading-5 break-words text-slate-600 sm:text-sm">
                        {skill.skill_name}
                      </Badge>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </section>
        )}

        {hasContent && (
          <article className="order-4 min-w-0 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm md:p-6 lg:p-8">
            {job.description && (
              <section aria-labelledby="job-description-heading">
                <h2 id="job-description-heading" className="text-xl font-semibold text-slate-900 md:text-[22px]">
                  Mô tả công việc
                </h2>
                <p className="mt-4 whitespace-pre-line break-words text-[15px] leading-[1.7] text-slate-600 md:text-base">
                  {job.description}
                </p>
              </section>
            )}
            {job.requirements && (
              <section className="mt-8" aria-labelledby="job-requirements-heading">
                <h2 id="job-requirements-heading" className="text-xl font-semibold text-slate-900 md:text-[22px]">
                  Yêu cầu
                </h2>
                <p className="mt-4 whitespace-pre-line break-words text-[15px] leading-[1.7] text-slate-600 md:text-base">
                  {job.requirements}
                </p>
              </section>
            )}
            {job.benefits && (
              <section className="mt-8" aria-labelledby="job-benefits-heading">
                <h2 id="job-benefits-heading" className="text-xl font-semibold text-slate-900 md:text-[22px]">
                  Phúc lợi
                </h2>
                <p className="mt-4 whitespace-pre-line break-words text-[15px] leading-[1.7] text-slate-600 md:text-base">
                  {job.benefits}
                </p>
              </section>
            )}
          </article>
        )}
      </div>

      <aside className="contents lg:sticky lg:top-[88px] lg:block lg:min-w-0 lg:space-y-6" aria-label="Thông tin ứng tuyển">
        <section className="order-3 min-w-0 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm md:p-6" aria-labelledby="application-heading">
          <div>
            <h2 id="application-heading" className="text-sm font-medium text-slate-500">Mức lương</h2>
            <p className="mt-1 flex min-w-0 items-start gap-2 text-2xl font-bold tracking-tight text-accent-600">
              <TrendingUp className="mt-1 size-5 shrink-0" aria-hidden="true" />
              <span className="min-w-0 break-words">{formatSalary(job)}</span>
            </p>
          </div>
          {job.location && (
            <div className="mt-5 flex gap-3 border-t border-slate-100 pt-5">
              <MapPin className="mt-0.5 size-5 shrink-0 text-primary" aria-hidden="true" />
              <div className="min-w-0">
                <p className="text-xs font-medium text-slate-400">Địa điểm</p>
                <p className="mt-1 break-words text-sm font-medium text-slate-700">{job.location}</p>
              </div>
            </div>
          )}
          <div className="mt-6">
            <ApplyButton jobId={job.id} className="w-full sm:w-full" />
          </div>
        </section>

        <section className="order-5 min-w-0 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm md:p-6" aria-labelledby="company-heading">
          <h2 id="company-heading" className="text-lg font-semibold text-slate-900">Về công ty</h2>
          <div className="mt-5 flex items-center gap-4">
            <span
              className="flex size-12 shrink-0 items-center justify-center rounded-xl bg-primary-50 text-lg font-bold text-primary ring-1 ring-primary/10"
              aria-hidden="true"
            >
              {job.company_name.charAt(0).toUpperCase()}
            </span>
            <p className="min-w-0 break-words font-semibold text-slate-800">{job.company_name}</p>
          </div>
        </section>
      </aside>
    </div>
  );
}
