import { authApiRequest } from "@/lib/api-client";
import type { Paginated } from "@/lib/types";
import type {
  AnalysisDto,
  ApplicationStatus,
  ApplicationTransitionStatus,
  CandidateApplicationDto,
  EmployerApplicationDto,
} from "@/features/applications/types";

export const getCandidateApplications = () =>
  authApiRequest<Paginated<CandidateApplicationDto>>("/api/applications/");

export const getCandidateApplication = (id: string) =>
  authApiRequest<CandidateApplicationDto>(`/api/applications/${id}/`);

export const applyToJob = (job: string, coverLetter: string) =>
  authApiRequest<CandidateApplicationDto>("/api/applications/", {
    method: "POST",
    body: JSON.stringify({ job, cover_letter: coverLetter }),
  });

export const getJobApplications = (
  jobId: string,
  status: ApplicationStatus | "" = "",
  ordering = "-match_score",
) => {
  const query = new URLSearchParams({ job: jobId, ordering });
  query.set("page_size", "100");
  if (status) query.set("status", status);
  return authApiRequest<Paginated<EmployerApplicationDto>>(`/api/applications/?${query}`);
};

export const getEmployerApplication = (id: string) =>
  authApiRequest<EmployerApplicationDto>(`/api/applications/${id}/`);

export const transitionApplication = (id: string, status: ApplicationTransitionStatus, note = "") =>
  authApiRequest<EmployerApplicationDto>(`/api/applications/${id}/status/`, {
    method: "POST",
    body: JSON.stringify({ status, note }),
  });

export const getApplicationAnalysis = (id: string) =>
  authApiRequest<AnalysisDto>(`/api/applications/${id}/analysis/`);
