import Link from "next/link";
import { MapPin, Sparkles, TrendingUp } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import type { JobDto } from "@/lib/types";
import { formatSalary, JOB_TYPE_LABELS, WORKPLACE_TYPE_LABELS } from "@/features/jobs/utils";

const LOGO_COLORS = [
  "bg-primary",
  "bg-accent",
  "bg-emerald-600",
  "bg-indigo-600",
  "bg-rose-600",
  "bg-cyan-600",
];

export function JobCard({ job, index = 0, showMatchScore = false }: { job: JobDto; index?: number; showMatchScore?: boolean }) {
  const color = LOGO_COLORS[index % LOGO_COLORS.length];
  const skills = job.skills.slice(0, 4);

  return (
    <Link
      href={`/jobs/${job.id}`}
      className="group flex flex-col rounded-xl border border-zinc-200 bg-white p-5 shadow-sm transition-all hover:-translate-y-0.5 hover:border-primary-200 hover:shadow-md"
    >
      <div className="flex items-start gap-4">
        <span
          className={`flex h-12 w-12 shrink-0 items-center justify-center rounded-xl ${color} text-lg font-bold text-white`}
        >
          {job.company_name.charAt(0).toUpperCase()}
        </span>
        <div className="min-w-0 flex-1">
          <h3 className="truncate font-semibold text-zinc-900 group-hover:text-primary">
            {job.title}
          </h3>
          <p className="mt-0.5 truncate text-sm text-zinc-500">{job.company_name}</p>
        </div>
        {showMatchScore && job.match_score !== null && (
          <Badge className="shrink-0 gap-1 bg-primary-50 text-primary">
            <Sparkles className="size-3" /> {Math.round(job.match_score)}%
          </Badge>
        )}
      </div>

      <div className="mt-4 flex flex-wrap items-center gap-2">
        <Badge variant="outline">{JOB_TYPE_LABELS[job.job_type]}</Badge>
        <Badge variant="outline">{WORKPLACE_TYPE_LABELS[job.workplace_type]}</Badge>
        {skills.map((skill) => (
          <Badge key={skill.id} variant="outline">
            {skill.skill_name}
          </Badge>
        ))}
      </div>

      <div className="mt-4 flex items-center justify-between gap-2 border-t border-zinc-100 pt-4">
        <span className="inline-flex items-center gap-1 text-sm font-medium text-accent-600">
          <TrendingUp className="h-4 w-4" />
          {formatSalary(job)}
        </span>
        <span className="inline-flex items-center gap-1 truncate text-sm text-zinc-500">
          <MapPin className="h-4 w-4 shrink-0" />
          <span className="truncate">{job.location || "—"}</span>
        </span>
      </div>
    </Link>
  );
}
