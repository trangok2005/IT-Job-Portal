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
// The register view returns UserSerializer at runtime; the generated schema
// currently describes this response as the narrower Register shape.
export type RegisterResponse = UserDto;
export type GoogleAuthPayload = components["schemas"]["GoogleAuthRequest"];

// Pagination metadata is identical for every DRF list response. Item DTOs still
// come directly from the generated OpenAPI components.
export type Paginated<T> = Omit<
  components["schemas"]["PaginatedJobReadList"],
  "results"
> & { results: T[] };
