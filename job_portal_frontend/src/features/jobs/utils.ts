import type { JobDto } from "@/lib/types";

export const JOB_TYPE_LABELS: Record<JobDto["job_type"], string> = {
  FULL_TIME: "Toàn thời gian",
  PART_TIME: "Bán thời gian",
  CONTRACT: "Hợp đồng / Freelance",
};

export const WORKPLACE_TYPE_LABELS: Record<JobDto["workplace_type"], string> = {
  ONSITE: "Tại văn phòng",
  HYBRID: "Linh hoạt (Hybrid)",
  REMOTE: "Từ xa (Remote)",
};

export const EXPERIENCE_LABELS: Record<JobDto["experience_level"], string> = {
  ENTRY: "Mới đi làm (Intern / Fresher)",
  JUNIOR: "Junior (1 - 2 năm)",
  MID_SENIOR: "Middle - Senior (3+ năm)",
  LEAD: "Trưởng nhóm / Quản lý",
};

export const LOCATION_OPTIONS: Array<{ value: JobDto["location"]; label: string }> = [
  { value: "Hồ Chí Minh", label: "Hồ Chí Minh" },
  { value: "Hà Nội", label: "Hà Nội" },
  { value: "Đà Nẵng", label: "Đà Nẵng" },
];

export function isJobType(value: string | undefined): value is JobDto["job_type"] {
  return value !== undefined && value in JOB_TYPE_LABELS;
}

export function isExperienceLevel(
  value: string | undefined,
): value is JobDto["experience_level"] {
  return value !== undefined && value in EXPERIENCE_LABELS;
}

export function isWorkplaceType(
  value: string | undefined,
): value is JobDto["workplace_type"] {
  return value !== undefined && value in WORKPLACE_TYPE_LABELS;
}

export function isLocation(value: string | undefined): value is JobDto["location"] {
  return value !== undefined && LOCATION_OPTIONS.some((option) => option.value === value);
}

export function formatSalary(job: Pick<JobDto, "salary_min" | "salary_max" | "salary_negotiable">) {
  if (job.salary_negotiable) return "Lương thỏa thuận";
  if (job.salary_min && job.salary_max) {
    return `${formatVnd(job.salary_min)} - ${formatVnd(job.salary_max)}`;
  }
  if (job.salary_min) return `Từ ${formatVnd(job.salary_min)}`;
  if (job.salary_max) return `Đến ${formatVnd(job.salary_max)}`;
  return "Lương thỏa thuận";
}

export function formatVnd(amount: number) {
  if (amount >= 1_000_000_000) {
    const value = amount / 1_000_000_000;
    return `${value % 1 === 0 ? value : value.toFixed(1)} tỷ`;
  }
  if (amount >= 1_000_000) {
    const value = amount / 1_000_000;
    return `${value % 1 === 0 ? value : value.toFixed(1)} triệu`;
  }
  return amount.toLocaleString("vi-VN");
}
