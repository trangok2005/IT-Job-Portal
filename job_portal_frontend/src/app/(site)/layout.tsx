import { PublicSiteShell } from "@/components/layout/public-site-shell";

export default function SiteLayout({ children }: LayoutProps<"/">) {
  return <PublicSiteShell>{children}</PublicSiteShell>;
}
