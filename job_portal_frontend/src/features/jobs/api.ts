import { authApiRequest } from "@/lib/api-client";
import type { Paginated, RecommendedJobDto } from "@/lib/types";

export function getRecommendedJobs(page = 1) {
  const query = new URLSearchParams({ page: String(page), page_size: "20" });
  return authApiRequest<Paginated<RecommendedJobDto>>(
    `/api/jobs/recommended/?${query.toString()}`,
  );
}
