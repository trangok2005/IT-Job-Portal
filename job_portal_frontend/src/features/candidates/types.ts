import type { components } from "@/types/generated/api-schema";

export type EducationDto = components["schemas"]["Education"];
export type EducationPayload = components["schemas"]["EducationRequest"];
export type DegreeLevel = components["schemas"]["DegreeLevelEnum"];
export type ExperienceDto = components["schemas"]["Experience"];
export type ExperiencePayload = components["schemas"]["ExperienceRequest"];
export type CandidateSkillDto = components["schemas"]["CandidateSkill"];
export type ResumeDto = components["schemas"]["Resume"];
export type PrivateFileURLDto = components["schemas"]["PrivateFileURL"];
export type CandidateProfileDto = components["schemas"]["CandidateProfileRead"];
export type ProfileUpdatePayload =
  components["schemas"]["PatchedCandidateProfileUpdateRequest"];
export type ProfileSavePayload = components["schemas"]["CandidateProfileSaveRequest"];
export type ResumeImportDto = components["schemas"]["ResumeImport"];
export type SkillOptionDto = components["schemas"]["SkillRead"];
export type ResumePreview = components["schemas"]["ResumeParsedData"];
