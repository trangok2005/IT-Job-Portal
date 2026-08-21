import type { components } from "@/types/generated/api-schema";

export type ApplicationStatus =
  components["schemas"]["CandidateApplicationRead"]["status"];
export type ApplicationTransitionStatus =
  components["schemas"]["ApplicationTransitionStatusEnum"];
export type ApplicationTransitionPayload =
  components["schemas"]["ApplicationTransitionRequest"];
export type StatusHistoryDto = components["schemas"]["ApplicationStatusHistory"];
export type SubmittedResumeDto = components["schemas"]["Resume"];
export type CandidateApplicationDto = components["schemas"]["CandidateApplicationRead"];
export type EmployerApplicationDto = components["schemas"]["EmployerApplicationRead"];
export type AnalysisDto = components["schemas"]["EmptyApplicationAnalysis"];
