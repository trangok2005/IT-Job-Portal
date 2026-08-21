import type {
  AdminCompanyQuery,
  AdminSkillDto,
  AdminSkillQuery,
  AdminUserQuery,
  CompanyDto,
  SkillCategoryDto,
  SkillCategoryPayload,
  SkillCreatePayload,
  SkillMergePayload,
  SkillUpdatePayload,
  UserDto,
  WeightConfigDto,
  WeightConfigPayload,
  WeightConfigUpdatePayload,
} from "@/features/admin/types";
import { authApiRequest } from "@/lib/api-client";
import type { Paginated } from "@/lib/types";

function json(method: string, body?: unknown): RequestInit {
  return {
    method,
    body: body === undefined ? undefined : JSON.stringify(body),
  };
}

function queryString(params: Record<string, string | number | boolean | undefined>) {
  const query = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== "") query.set(key, String(value));
  }
  return query.toString();
}

export const getAdminCompanies = (params: AdminCompanyQuery = {}) =>
  authApiRequest<Paginated<CompanyDto>>(
    `/api/companies/?${queryString({ page_size: 100, ...params })}`,
  );

export const approveCompany = (id: string) =>
  authApiRequest<CompanyDto>(`/api/companies/${id}/approve/`, json("POST"));

export const rejectCompany = (id: string, rejectionReason: string) =>
  authApiRequest<CompanyDto>(
    `/api/companies/${id}/reject/`,
    json("POST", { rejection_reason: rejectionReason }),
  );

export const lockCompany = (id: string) =>
  authApiRequest<CompanyDto>(`/api/companies/${id}/lock/`, json("POST"));

export const getAdminUsers = (params: AdminUserQuery = {}) =>
  authApiRequest<Paginated<UserDto>>(
    `/api/accounts/users/?${queryString({ page_size: 100, ...params })}`,
  );

export const setUserLocked = (id: string, locked: boolean) =>
  authApiRequest<UserDto>(
    `/api/accounts/users/${id}/${locked ? "lock" : "unlock"}/`,
    json("POST"),
  );

export const getAdminSkills = (params: AdminSkillQuery = {}) =>
  authApiRequest<Paginated<AdminSkillDto>>(
    `/api/skills/?${queryString({ page_size: 100, ...params })}`,
  );

export const createAdminSkill = (payload: SkillCreatePayload) =>
  authApiRequest<AdminSkillDto>("/api/skills/", json("POST", payload));

export const updateAdminSkill = (id: string, payload: SkillUpdatePayload) =>
  authApiRequest<AdminSkillDto>(`/api/skills/${id}/`, json("PATCH", payload));

export const reviewSkill = (id: string, action: "approve" | "reject") =>
  authApiRequest<AdminSkillDto>(`/api/skills/${id}/${action}/`, json("POST"));

export const mergeSkills = (payload: SkillMergePayload) =>
  authApiRequest<AdminSkillDto>("/api/skills/merge/", json("POST", payload));

export const getSkillCategories = () =>
  authApiRequest<Paginated<SkillCategoryDto>>("/api/skill-categories/?page_size=100");

export const createSkillCategory = (payload: SkillCategoryPayload) =>
  authApiRequest<SkillCategoryDto>("/api/skill-categories/", json("POST", payload));

export const getWeightConfigs = () =>
  authApiRequest<Paginated<WeightConfigDto>>("/api/weight-configs/?page_size=100");

export const createWeightConfig = (payload: WeightConfigPayload) =>
  authApiRequest<WeightConfigDto>("/api/weight-configs/", json("POST", payload));

export const updateWeightConfig = (id: string, payload: WeightConfigUpdatePayload) =>
  authApiRequest<WeightConfigDto>(`/api/weight-configs/${id}/`, json("PATCH", payload));
