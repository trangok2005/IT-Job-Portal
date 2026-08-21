import { JobApplications } from "@/features/employer/components/job-applications";
export default async function JobApplicationsPage({ params }: PageProps<"/employer/jobs/[id]/applications">) { const { id } = await params; return <JobApplications jobId={id} />; }
