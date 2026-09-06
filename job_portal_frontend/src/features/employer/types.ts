import type { components } from "@/types/generated/api-schema";

export type CompanyStatus = components["schemas"]["CompanyReadStatusEnum"];
export type CompanyDto = Omit<components["schemas"]["CompanyRead"], "logo_url">;
export type CompanyUpdatePayload = Omit<
  components["schemas"]["PatchedCompanyWriteRequest"],
  "logo_url"
>;
export type EmployerJobDto = components["schemas"]["EmployerJobRead"];
export type JobPayload = components["schemas"]["JobWriteRequest"];
export type JobUpdatePayload = components["schemas"]["PatchedJobWriteRequest"];
export type RequiredEducationLevel = components["schemas"]["RequiredEducationLevelEnum"];
export type JDImportDto = components["schemas"]["JDImport"];
export type SkillDto = components["schemas"]["SkillRead"];
export type RecommendedCandidateDto = components["schemas"]["RecommendedCandidate"];

export const COMPANY_STATUS_LABELS: Record<CompanyStatus, string> = {
  PENDING: "Chờ duyệt",
  APPROVED: "Đã duyệt",
  REJECTED: "Bị từ chối",
  LOCKED: "Đã khóa",
};

export const JOB_STATUS_LABELS: Record<EmployerJobDto["status"], string> = {
  DRAFT: "Bản nháp",
  ACTIVE: "Đang tuyển",
  CLOSED: "Đã đóng",
  EXPIRED: "Hết hạn",
};
