import type { JobDto } from "@/lib/types";

export const JOB_TYPE_LABELS: Record<JobDto["job_type"], string> = {
  FULL_TIME: "Toàn thời gian",
  PART_TIME: "Bán thời gian",
  INTERNSHIP: "Thực tập",
  CONTRACT: "Hợp đồng",
  REMOTE: "Từ xa",
};

export const EXPERIENCE_LABELS: Record<JobDto["experience_level"], string> = {
  INTERN: "Thực tập sinh",
  FRESHER: "Mới tốt nghiệp",
  JUNIOR: "Junior",
  MIDDLE: "Middle",
  SENIOR: "Senior",
  LEAD: "Lead / Manager",
};

export function isJobType(value: string | undefined): value is JobDto["job_type"] {
  return value !== undefined && value in JOB_TYPE_LABELS;
}

export function isExperienceLevel(
  value: string | undefined,
): value is JobDto["experience_level"] {
  return value !== undefined && value in EXPERIENCE_LABELS;
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

export function companyInitial(name: string) {
  return name.trim().charAt(0).toUpperCase() || "J";
}
