import { apiRequest } from "@/lib/api-client";
import { getAccessToken } from "@/lib/auth";
import type { Paginated } from "@/lib/types";
import type {
  CandidateProfileDto,
  ProfileSavePayload,
  ResumeDto,
  ResumeImportDto,
  SkillOptionDto,
} from "@/features/candidates/types";

function authHeaders(): HeadersInit {
  const token = getAccessToken();
  if (!token) throw new Error("Phiên đăng nhập đã hết hạn. Vui lòng đăng nhập lại.");
  return { Authorization: `Bearer ${token}` };
}

function jsonInit(method: string, payload?: unknown): RequestInit {
  return {
    method,
    headers: authHeaders(),
    body: payload === undefined ? undefined : JSON.stringify(payload),
  };
}

export const getCandidateProfile = () =>
  apiRequest<CandidateProfileDto>("/api/candidates/me/", {
    headers: authHeaders(),
  });

export const saveCandidateProfile = (payload: ProfileSavePayload) =>
  apiRequest<CandidateProfileDto>(
    "/api/candidates/me/",
    jsonInit("PUT", payload),
  );

export const getSkillOptions = () =>
  apiRequest<Paginated<SkillOptionDto>>("/api/skills/?page_size=100");

export function uploadResume(file: File, isPrimary = false) {
  const body = new FormData();
  body.set("file", file);
  body.set("is_primary", String(isPrimary));
  return apiRequest<ResumeDto>("/api/candidates/me/resumes/", {
    method: "POST",
    headers: authHeaders(),
    body,
  });
}

export const deleteResume = (id: string) =>
  apiRequest<void>(
    `/api/candidates/me/resumes/${id}/`,
    jsonInit("DELETE"),
  );

export const setPrimaryResume = (id: string) =>
  apiRequest<ResumeDto>(
    `/api/candidates/me/resumes/${id}/set-primary/`,
    jsonInit("POST"),
  );

export function parseResumeImport(file: File) {
  const body = new FormData();
  body.set("file", file);
  return apiRequest<ResumeImportDto>("/api/candidates/me/resume-imports/", {
    method: "POST",
    headers: authHeaders(),
    body,
  });
}

export const getResumeImport = (id: string) =>
  apiRequest<ResumeImportDto>(
    `/api/candidates/me/resume-imports/${id}/`,
    { headers: authHeaders() },
  );

export function cancelResumeImport(resumeImportId: string) {
  return apiRequest<void>(
    `/api/candidates/me/resume-imports/${resumeImportId}/`,
    jsonInit("DELETE"),
  );
}
