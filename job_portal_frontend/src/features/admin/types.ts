import type { components, operations } from "@/types/generated/api-schema";
import type { CompanyDto } from "@/features/employer/types";
import type { UserDto } from "@/lib/types";

export { type CompanyDto, type UserDto };
export type AdminSkillDto = components["schemas"]["SkillRead"];
export type SkillCategoryDto = components["schemas"]["SkillCategory"];
export type WeightConfigDto = components["schemas"]["MatchingWeightConfig"];
export type SkillCreatePayload = components["schemas"]["SkillWriteRequest"];
export type SkillUpdatePayload = components["schemas"]["PatchedSkillWriteRequest"];
export type SkillMergePayload = components["schemas"]["SkillMergeRequest"];
export type SkillCategoryPayload = components["schemas"]["SkillCategoryRequest"];
export type WeightConfigPayload = components["schemas"]["MatchingWeightConfigRequest"];
export type WeightConfigUpdatePayload =
  components["schemas"]["PatchedMatchingWeightConfigRequest"];
export type AdminUserQuery = NonNullable<
  operations["accounts_users_list"]["parameters"]["query"]
>;
export type AdminCompanyQuery = NonNullable<
  operations["companies_list"]["parameters"]["query"]
>;
export type AdminSkillQuery = NonNullable<
  operations["skills_list"]["parameters"]["query"]
>;
