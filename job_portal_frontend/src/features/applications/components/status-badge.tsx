import { Badge } from "@/components/ui/badge";
import type { ApplicationStatus, MatchStatus } from "@/features/applications/types";

export const applicationStatusLabel: Record<ApplicationStatus, string> = {
  APPLIED: "Đã nộp",
  SHORTLISTED: "Qua sơ tuyển",
  INTERVIEWED: "Đã phỏng vấn",
  HIRED: "Đã tuyển",
  REJECTED: "Từ chối",
};

const applicationStatusClassName: Record<ApplicationStatus, string> = {
  APPLIED: "border-blue-200 bg-blue-50 text-blue-700",
  SHORTLISTED: "border-violet-200 bg-violet-50 text-violet-700",
  INTERVIEWED: "border-amber-200 bg-amber-50 text-amber-700",
  HIRED: "border-emerald-200 bg-emerald-50 text-emerald-700",
  REJECTED: "border-red-200 bg-red-50 text-red-700",
};

export const matchStatusLabel: Record<MatchStatus, string> = {
  PENDING: "Đang chờ tính điểm",
  PROCESSING: "Đang tính điểm",
  COMPLETED: "Đã tính điểm",
  FAILED: "Không thể tính điểm",
  INSUFFICIENT: "Chưa đủ điều kiện tính điểm",
};

export function ApplicationStatusBadge({ status }: { status: ApplicationStatus }) {
  return <Badge variant="outline" className={applicationStatusClassName[status]}>{applicationStatusLabel[status]}</Badge>;
}
