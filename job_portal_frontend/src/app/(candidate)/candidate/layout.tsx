import { PublicSiteShell } from "@/components/layout/public-site-shell";
import { RequireRole } from "@/features/auth/components/require-role";
import { CandidateResumeImportProvider } from "@/features/candidates/candidate-resume-import-provider";

export default function CandidateLayout({ children }: { children: React.ReactNode }) {
  return (
    <CandidateResumeImportProvider>
      <RequireRole roles={["CANDIDATE"]}>
        <PublicSiteShell>{children}</PublicSiteShell>
      </RequireRole>
    </CandidateResumeImportProvider>
  );
}
