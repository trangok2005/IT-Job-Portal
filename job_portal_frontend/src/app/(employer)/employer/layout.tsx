import { PublicSiteShell } from "@/components/layout/public-site-shell";
import { RequireRole } from "@/features/auth/components/require-role";
import { CompanyGate } from "@/features/employer/components/company-gate";

export default function EmployerLayout({ children }: { children: React.ReactNode }) {
  return (
    <RequireRole roles={["EMPLOYER"]}>
      <PublicSiteShell>
        <CompanyGate>{children}</CompanyGate>
      </PublicSiteShell>
    </RequireRole>
  );
}
