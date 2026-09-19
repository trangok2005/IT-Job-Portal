import type { components } from "@/types/generated/api-schema";

export type UserRole = components["schemas"]["UserRoleEnum"];
export type UserDto = components["schemas"]["User"];
export type AuthTokens = components["schemas"]["TokenObtainPair"];
export type GoogleAuthResponse = components["schemas"]["GoogleAuthResponse"];
export type JobSkillDto = components["schemas"]["JobSkill"];
export type JobDto = components["schemas"]["JobRead"];
export type RecommendedJobDto = components["schemas"]["RecommendedJob"];
export type LoginPayload = components["schemas"]["TokenObtainPairRequest"];
export type RegisterPayload = components["schemas"]["RegisterRequest"];
// API trả User dù schema register đang mô tả kiểu hẹp hơn.
export type RegisterResponse = UserDto;
export type GoogleAuthPayload = components["schemas"]["GoogleAuthRequest"];

// Các list DRF dùng chung metadata phân trang.
export type Paginated<T> = Omit<
  components["schemas"]["PaginatedJobReadList"],
  "results"
> & { results: T[] };
