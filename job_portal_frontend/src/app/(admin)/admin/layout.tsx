import { PublicSiteShell } from "@/components/layout/public-site-shell";
import { RequireRole } from "@/features/auth/components/require-role";

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  return (
    <RequireRole roles={["ADMIN"]}>
      <PublicSiteShell>{children}</PublicSiteShell>
    </RequireRole>
  );
}
