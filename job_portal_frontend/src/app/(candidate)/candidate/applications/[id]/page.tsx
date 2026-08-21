import { CandidateApplicationDetail } from "@/features/applications/components/candidate-application-detail";

export default async function ApplicationDetailPage({ params }: PageProps<"/candidate/applications/[id]">) { const { id } = await params; return <CandidateApplicationDetail id={id} />; }
