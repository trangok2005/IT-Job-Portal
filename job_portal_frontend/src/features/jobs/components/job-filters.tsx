"use client";

import {
  EXPERIENCE_LABELS,
  JOB_TYPE_LABELS,
  LOCATION_OPTIONS,
  WORKPLACE_TYPE_LABELS,
} from "@/features/jobs/utils";
import type { JobDto } from "@/lib/types";
import { useRouter } from "next/navigation";

export function JobFilters({
  workplaceType,
  jobType,
  experienceLevel,
  salaryMin,
  location,
}: {
  workplaceType?: JobDto["workplace_type"];
  jobType?: JobDto["job_type"];
  experienceLevel?: JobDto["experience_level"];
  salaryMin?: number;
  location?: JobDto["location"];
}) {
  const router = useRouter();
  const updateParam = (key: string, value: string) => {
    const params = new URLSearchParams(window.location.search);
    if (value) params.set(key, value);
    else params.delete(key);
    params.set("tab", "all");
    params.delete("page");
    router.push(`/jobs${params.size ? `?${params.toString()}` : ""}`);
  };

  return (
    <div className="flex flex-wrap gap-2">
      <select
        value={workplaceType ?? ""}
        onChange={(e) => updateParam("workplace_type", e.target.value)}
        className="h-10 rounded-xl border border-zinc-300 bg-white px-3 text-sm text-zinc-700"
      >
        <option value="">Nơi làm việc</option>
        {Object.entries(WORKPLACE_TYPE_LABELS).map(([value, label]) => (
          <option key={value} value={value}>{label}</option>
        ))}
      </select>
      <select
        value={jobType ?? ""}
        onChange={(e) => updateParam("job_type", e.target.value)}
        className="h-10 rounded-xl border border-zinc-300 bg-white px-3 text-sm text-zinc-700"
      >
        <option value="">Loại hình</option>
        {Object.entries(JOB_TYPE_LABELS).map(([value, label]) => (
          <option key={value} value={value}>
            {label}
          </option>
        ))}
      </select>
      <select
        value={experienceLevel ?? ""}
        onChange={(e) => updateParam("experience_level", e.target.value)}
        className="h-10 rounded-xl border border-zinc-300 bg-white px-3 text-sm text-zinc-700"
      >
        <option value="">Kinh nghiệm</option>
        {Object.entries(EXPERIENCE_LABELS).map(([value, label]) => (
          <option key={value} value={value}>
            {label}
          </option>
        ))}
      </select>
      <select
        value={location ?? ""}
        onChange={(e) => updateParam("location", e.target.value)}
        className="h-10 rounded-xl border border-zinc-300 bg-white px-3 text-sm text-zinc-700"
      >
        <option value="">Địa điểm</option>
        {LOCATION_OPTIONS.map((option) => (
          <option key={option.value} value={option.value}>{option.label}</option>
        ))}
      </select>
      <select
        value={salaryMin?.toString() ?? ""}
        onChange={(e) => updateParam("salary_min", e.target.value)}
        className="h-10 rounded-xl border border-zinc-300 bg-white px-3 text-sm text-zinc-700"
      >
        <option value="">Mức lương</option>
        {[10, 15, 20, 30, 50].map((millions) => (
          <option key={millions} value={millions * 1_000_000}>
            Từ {millions} triệu
          </option>
        ))}
      </select>
    </div>
  );
}
