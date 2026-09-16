import { apiRequest, authApiRequest } from "@/lib/api-client";
import type { JobDto, Paginated } from "@/lib/types";
import type {
  CompanyDto,
  CompanyUpdatePayload,
  EmployerJobDto,
  JDImportDto,
  JobPayload,
  JobUpdatePayload,
  RecommendedCandidateDto,
  SkillDto,
} from "@/features/employer/types";

function jsonInit(method: string, payload?: unknown): RequestInit {
  return {
    method,
    body: payload === undefined ? undefined : JSON.stringify(payload),
  };
}

export const getMyCompany = () => authApiRequest<CompanyDto>("/api/companies/me/");

export const updateMyCompany = (payload: CompanyUpdatePayload) =>
  authApiRequest<CompanyDto>("/api/companies/me/", jsonInit("PATCH", payload));

export const resubmitCompany = (id: string) =>
  authApiRequest<CompanyDto>(`/api/companies/${id}/resubmit/`, jsonInit("POST"));

export const getMyJobs = (page = 1) =>
  authApiRequest<Paginated<EmployerJobDto>>(`/api/jobs/my-jobs/?page=${page}`);

export const getEmployerJob = (id: string) =>
  authApiRequest<JobDto>(`/api/jobs/${id}/`);

export const createEmployerJob = (payload: JobPayload) =>
  authApiRequest<JobDto>("/api/jobs/", jsonInit("POST", payload));

export const updateEmployerJob = (id: string, payload: JobUpdatePayload) =>
  authApiRequest<JobDto>(`/api/jobs/${id}/`, jsonInit("PATCH", payload));

export const publishEmployerJob = (id: string) =>
  authApiRequest<JobDto>(`/api/jobs/${id}/publish/`, jsonInit("POST"));

export const closeEmployerJob = (id: string) =>
  authApiRequest<JobDto>(`/api/jobs/${id}/close/`, jsonInit("POST"));

export const getEmployerSkills = () =>
  apiRequest<Paginated<SkillDto>>("/api/skills/?page_size=100");

export const getRecommendedCandidates = (jobId: string, page = 1) =>
  authApiRequest<Paginated<RecommendedCandidateDto>>(
    `/api/jobs/${jobId}/recommended-candidates/?page_size=20&page=${page}`,
  );

export const parseJobDescription = (file: File) => {
  const body = new FormData();
  body.set("file", file);
  return authApiRequest<JDImportDto>("/api/jobs/parse-jd/", {
    method: "POST",
    body,
  });
};

export const getJDImport = (id: string) =>
  authApiRequest<JDImportDto>(`/api/jobs/jd-imports/${id}/`);

export const cancelJDImport = (id: string) =>
  authApiRequest<void>(`/api/jobs/jd-imports/${id}/`, { method: "DELETE" });
