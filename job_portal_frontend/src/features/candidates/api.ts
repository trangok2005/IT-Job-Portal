import { apiRequest, authApiRequest } from "@/lib/api-client";
import type { Paginated } from "@/lib/types";
import type {
  CandidateProfileDto,
  PrivateFileURLDto,
  ProfileSavePayload,
  ResumeDto,
  ResumeImportDto,
  SkillOptionDto,
} from "@/features/candidates/types";

function jsonInit(method: string, payload?: unknown): RequestInit {
  return {
    method,
    body: payload === undefined ? undefined : JSON.stringify(payload),
  };
}

export const getCandidateProfile = (signal?: AbortSignal) =>
  authApiRequest<CandidateProfileDto>("/api/candidates/me/", { signal });

export const saveCandidateProfile = (payload: ProfileSavePayload) =>
  authApiRequest<CandidateProfileDto>(
    "/api/candidates/me/",
    jsonInit("PUT", payload),
  );

export const getSkillOptions = () =>
  apiRequest<Paginated<SkillOptionDto>>("/api/skills/?page_size=100");

export const deleteResume = (id: string) =>
  authApiRequest<void>(
    `/api/candidates/me/resumes/${id}/`,
    jsonInit("DELETE"),
  );

export const getResumeDownloadURL = (id: string) =>
  authApiRequest<PrivateFileURLDto>(
    `/api/candidates/me/resumes/${id}/download-url/`,
  );

export const setPrimaryResume = (id: string) =>
  authApiRequest<ResumeDto>(
    `/api/candidates/me/resumes/${id}/set-primary/`,
    jsonInit("POST"),
  );

export function parseResumeImport(file: File) {
  const body = new FormData();
  body.set("file", file);
  return authApiRequest<ResumeImportDto>("/api/candidates/me/resume-imports/", {
    method: "POST",
    body,
  });
}

export const getResumeImport = (id: string) =>
  authApiRequest<ResumeImportDto>(
    `/api/candidates/me/resume-imports/${id}/`,
  );

export function cancelResumeImport(resumeImportId: string) {
  return authApiRequest<void>(
    `/api/candidates/me/resume-imports/${resumeImportId}/`,
    jsonInit("DELETE"),
  );
}
