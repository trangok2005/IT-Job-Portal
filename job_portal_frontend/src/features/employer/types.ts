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
export type JobDescriptionParseResult =
  components["schemas"]["JobDescriptionParseResult"];
export type JDImportDto = components["schemas"]["JDImport"];
export type SkillDto = components["schemas"]["SkillRead"];
export type RecommendedCandidateDto = components["schemas"]["RecommendedCandidate"];
