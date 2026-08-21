import { JobForm } from "@/features/employer/components/job-form";
export default async function EditJobPage({ params }: PageProps<"/employer/jobs/[id]/edit">) { const { id } = await params; return <JobForm jobId={id} />; }
