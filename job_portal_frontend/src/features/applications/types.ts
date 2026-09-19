import type { components } from "@/types/generated/api-schema";

export type ApplicationStatus = components["schemas"]["CandidateApplicationRead"]["status"];
export type ApplicationTransitionStatus =components["schemas"]["ApplicationTransitionStatusEnum"];
export type ApplicationTransitionPayload =components["schemas"]["ApplicationTransitionRequest"];
export type ApplicationCreatePayload =components["schemas"]["ApplicationCreateRequest"];
export type StatusHistoryDto = components["schemas"]["ApplicationStatusHistory"];
export type CandidateApplicationDto = components["schemas"]["CandidateApplicationRead"];
export type EmployerApplicationDto = components["schemas"]["EmployerApplicationRead"];
export type ApplicationMatchResultDto =components["schemas"]["EmptyApplicationMatchResult"];
export type MatchStatus = components["schemas"]["MatchStatusEnum"];
export type PrivateFileURLDto = components["schemas"]["PrivateFileURL"];
