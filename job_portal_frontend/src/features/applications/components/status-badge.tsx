import { Badge } from "@/components/ui/badge";
import type { ApplicationStatus } from "@/features/applications/types";

export const applicationStatusLabel: Record<ApplicationStatus, string> = {
  APPLIED: "Đã ứng tuyển",
  SHORTLISTED: "Đã chọn lọc",
  INTERVIEWED: "Đã phỏng vấn",
  HIRED: "Đã tuyển",
  REJECTED: "Đã từ chối",
};

export function ApplicationStatusBadge({ status }: { status: ApplicationStatus }) {
  const variant = status === "HIRED" ? "success" : status === "REJECTED" ? "outline" : status === "INTERVIEWED" ? "accent" : "default";
  return <Badge variant={variant}>{applicationStatusLabel[status]}</Badge>;
}
