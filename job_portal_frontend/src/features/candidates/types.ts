import type { components } from "@/types/generated/api-schema";

export type EducationDto = components["schemas"]["Education"];
export type EducationPayload = components["schemas"]["EducationRequest"];
export type EducationUpdatePayload = components["schemas"]["PatchedEducationRequest"];
export type ExperienceDto = components["schemas"]["Experience"];
export type ExperiencePayload = components["schemas"]["ExperienceRequest"];
export type ExperienceUpdatePayload = components["schemas"]["PatchedExperienceRequest"];
export type CandidateSkillDto = components["schemas"]["CandidateSkill"] & {
  skill_status?: string;
};
export type CandidateSkillPayload = components["schemas"]["CandidateSkillRequest"];
export type CandidateSkillUpdatePayload =
  components["schemas"]["PatchedCandidateSkillRequest"];
export type ResumeDto = components["schemas"]["Resume"];
export type CandidateProfileDto = components["schemas"]["CandidateProfileRead"];
export type ProfileUpdatePayload =
  components["schemas"]["PatchedCandidateProfileUpdateRequest"];
export type ProfileSavePayload = Omit<
  components["schemas"]["CandidateProfileSaveRequest"],
  "resume_id"
> & { resume_import_id?: string | null };

// TODO: đổi lại thành components["schemas"]["ResumeImport"] sau khi chạy
// `npm run api:types` với backend đang bật (schema đã thêm endpoint mới).
export type ResumeImportDto = {
  id: string;
  original_filename: string;
  file_size_bytes: number | null;
  parse_status: "PENDING" | "SUCCESS" | "FAILED" | "CONSUMED";
  parse_error_message: string;
  parsed_data: ResumePreview | null;
  expires_at: string | null;
  file_url: string;
  created_at: string;
  updated_at: string;
};
export type SkillOptionDto = components["schemas"]["SkillRead"];
export type ResumePreview = {
  full_name?: string;
  phone?: string;
  headline?: string;
  summary?: string;
  educations?: Array<Omit<EducationPayload, "source">>;
  experiences?: Array<Omit<ExperiencePayload, "source">>;
  skills?: string[];
};
