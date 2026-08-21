import { EmployerApplicationDetail } from "@/features/employer/components/application-detail";

export default async function EmployerApplicationPage({
  params,
}: PageProps<"/employer/jobs/[id]/applications/[appId]">) {
  const { id, appId } = await params;
  return <EmployerApplicationDetail id={appId} jobId={id} />;
}
