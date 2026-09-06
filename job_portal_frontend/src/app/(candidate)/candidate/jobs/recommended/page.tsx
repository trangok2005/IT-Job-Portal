import { redirect } from "next/navigation";

export default function RecommendedJobsPage() {
  redirect("/jobs?tab=recommended");
}
