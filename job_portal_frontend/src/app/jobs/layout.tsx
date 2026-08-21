import { PublicSiteShell } from "@/components/layout/public-site-shell";

export default function JobsLayout({ children }: { children: React.ReactNode }) {
  return <PublicSiteShell>{children}</PublicSiteShell>;
}
