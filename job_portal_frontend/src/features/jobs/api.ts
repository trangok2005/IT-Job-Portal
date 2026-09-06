import { authApiRequest } from "@/lib/api-client";
import type { Paginated, RecommendedJobDto } from "@/lib/types";

export function getRecommendedJobs(signal?: AbortSignal) {
  const query = new URLSearchParams({ page_size: "9" });
  return authApiRequest<Paginated<RecommendedJobDto>>(
    `/api/jobs/recommended/?${query.toString()}`,
    { signal },
  );
}
