import { PublicSiteShell } from "@/components/layout/public-site-shell";
import { RequireRole } from "@/features/auth/components/require-role";

export default function CandidateLayout({ children }: { children: React.ReactNode }) {
  return (
    <RequireRole roles={["CANDIDATE"]}>
      <PublicSiteShell>{children}</PublicSiteShell>
    </RequireRole>
  );
}
