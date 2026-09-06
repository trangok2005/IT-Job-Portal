import { MapPin, TrendingUp } from "lucide-react";

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

  return (
    <div className="rounded-xl border border-zinc-200 bg-white p-6 shadow-sm sm:p-8">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start">
        <span className="flex h-14 w-14 shrink-0 items-center justify-center rounded-xl bg-primary text-xl font-bold text-white">
          {job.company_name.charAt(0).toUpperCase()}
        </span>
        <div className="min-w-0 flex-1">
          <Title className="text-2xl font-bold text-zinc-900">{job.title}</Title>
          <p className="mt-1 text-sm text-zinc-500">{job.company_name}</p>
          <div className="mt-3 flex flex-wrap items-center gap-2">
            <Badge variant="default">{JOB_TYPE_LABELS[job.job_type] ?? job.job_type}</Badge>
            <Badge variant="outline">{WORKPLACE_TYPE_LABELS[job.workplace_type]}</Badge>
            {job.experience_level && (
              <Badge variant="outline">
                {EXPERIENCE_LABELS[job.experience_level] ?? job.experience_level}
              </Badge>
            )}
            {job.required_education_level && (
              <Badge variant="outline">
                Học vấn: {EDUCATION_LABELS[job.required_education_level]}
              </Badge>
            )}
          </div>
          {job.skills.length > 0 && (
            <div className="mt-4 space-y-2 text-sm">
              {requiredSkills.length > 0 && (
                <div className="flex flex-wrap items-center gap-2">
                  <span className="w-full text-xs font-medium text-zinc-500 sm:w-20">Bắt buộc</span>
                  {requiredSkills.map((skill) => (
                    <Badge key={skill.id}>{skill.skill_name}</Badge>
                  ))}
                </div>
              )}
              {preferredSkills.length > 0 && (
                <div className="flex flex-wrap items-center gap-2">
                  <span className="w-full text-xs font-medium text-zinc-500 sm:w-20">Ưu tiên</span>
                  {preferredSkills.map((skill) => (
                    <Badge key={skill.id} variant="outline">{skill.skill_name}</Badge>
                  ))}
                </div>
              )}
            </div>
          )}
          <div className="mt-5"><ApplyButton jobId={job.id} /></div>
        </div>
      </div>

      <div className="mt-6 grid gap-3 rounded-xl bg-zinc-50 p-4 text-sm sm:grid-cols-2">
        <span className="inline-flex items-center gap-2 font-medium text-accent-600">
          <TrendingUp className="h-4 w-4" /> {formatSalary(job)}
        </span>
        <span className="inline-flex items-center gap-2 text-zinc-600">
          <MapPin className="h-4 w-4" /> {job.location || "—"}
        </span>
      </div>

      {job.description && (
        <section className="mt-8">
          <h3 className="text-lg font-semibold text-zinc-900">Mô tả công việc</h3>
          <p className="mt-3 whitespace-pre-line text-sm leading-relaxed text-zinc-600">{job.description}</p>
        </section>
      )}
      {job.requirements && (
        <section className="mt-8">
          <h3 className="text-lg font-semibold text-zinc-900">Yêu cầu</h3>
          <p className="mt-3 whitespace-pre-line text-sm leading-relaxed text-zinc-600">{job.requirements}</p>
        </section>
      )}
      {job.benefits && (
        <section className="mt-8">
          <h3 className="text-lg font-semibold text-zinc-900">Phúc lợi</h3>
          <p className="mt-3 whitespace-pre-line text-sm leading-relaxed text-zinc-600">{job.benefits}</p>
        </section>
      )}
    </div>
  );
}
