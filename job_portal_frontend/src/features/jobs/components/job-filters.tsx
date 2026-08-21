"use client";

import { EXPERIENCE_LABELS, JOB_TYPE_LABELS } from "@/features/jobs/utils";
import { useRouter } from "next/navigation";

export function JobFilters({
  jobType,
  experienceLevel,
  salaryMin,
}: {
  jobType?: string;
  experienceLevel?: string;
  salaryMin?: number;
}) {
  const router = useRouter();
  const updateParam = (key: string, value: string) => {
    const params = new URLSearchParams(window.location.search);
    if (value) params.set(key, value);
    else params.delete(key);
    params.delete("page");
    router.push(`/jobs${params.size ? `?${params.toString()}` : ""}`);
  };

  return (
    <div className="flex flex-wrap gap-2">
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
