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
// Register view trả về UserSerializer khi chạy; schema được sinh hiện mô tả
// response này bằng cấu trúc Register hẹp hơn.
export type RegisterResponse = UserDto;
export type GoogleAuthPayload = components["schemas"]["GoogleAuthRequest"];

// Metadata phân trang giống nhau cho mọi list response của DRF. Item DTO vẫn
// lấy trực tiếp từ các OpenAPI component được sinh.
export type Paginated<T> = Omit<
  components["schemas"]["PaginatedJobReadList"],
  "results"
> & { results: T[] };
