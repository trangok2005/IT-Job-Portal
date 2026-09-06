import { authApiRequest } from "@/lib/api-client";
import type { Paginated } from "@/lib/types";
import type {
  ApplicationMatchResultDto,
  ApplicationCreatePayload,
  ApplicationStatus,
  ApplicationTransitionPayload,
  CandidateApplicationDto,
  EmployerApplicationDto,
  PrivateFileURLDto,
} from "@/features/applications/types";

export const getCandidateApplications = (
  page = 1,
  status: ApplicationStatus | "" = "",
  ordering = "-created_at",
  signal?: AbortSignal,
) => {
  const query = new URLSearchParams({ page: String(page), ordering });
  if (status) query.set("status", status);
  return authApiRequest<Paginated<CandidateApplicationDto>>(`/api/applications/?${query}`, { signal });
};

export const getCandidateApplication = (id: string, signal?: AbortSignal) =>
  authApiRequest<CandidateApplicationDto>(`/api/applications/${id}/`, { signal });

export const applyToJob = (payload: ApplicationCreatePayload) =>
  authApiRequest<CandidateApplicationDto>("/api/applications/", {
    method: "POST",
    body: JSON.stringify(payload),
  });

export const getJobApplications = (
  jobId: string,
  status: ApplicationStatus | "" = "",
  ordering = "-match_score",
  page = 1,
) => {
  const query = new URLSearchParams({ job: jobId, ordering, page: String(page) });
  if (status) query.set("status", status);
  return authApiRequest<Paginated<EmployerApplicationDto>>(`/api/applications/?${query}`);
};

export const getEmployerApplication = (id: string) =>
  authApiRequest<EmployerApplicationDto>(`/api/applications/${id}/`);

export const transitionApplication = (id: string, payload: ApplicationTransitionPayload) =>
  authApiRequest<EmployerApplicationDto>(`/api/applications/${id}/status/`, {
    method: "POST",
    body: JSON.stringify(payload),
  });

export const getApplicationMatchResult = (id: string) =>
  authApiRequest<ApplicationMatchResultDto>(
    `/api/applications/${id}/match-result/`,
  );

export const getApplicationResumeDownloadURL = (id: string) =>
  authApiRequest<PrivateFileURLDto>(
    `/api/applications/${id}/resume-download-url/`,
  );
