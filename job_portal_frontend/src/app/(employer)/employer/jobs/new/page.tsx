import { JobForm } from "@/features/employer/components/job-form";

export default async function NewJobPage({ searchParams }: PageProps<"/employer/jobs/new">) {
  const { import_id: importId } = await searchParams;
  return <JobForm importId={typeof importId === "string" ? importId : undefined} />;
}
