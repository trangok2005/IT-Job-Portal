"use client";

import { usePathname, useRouter } from "next/navigation";
import { useEffect } from "react";

import { ROLE_HOME } from "@/lib/auth";
import { useAuth } from "@/lib/auth-provider";
import type { UserRole } from "@/lib/types";

export function RequireRole({
  roles,
  children,
}: {
  roles: UserRole[];
  children: React.ReactNode;
}) {
  const { user } = useAuth();
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    if (!user) {
      router.replace(`/login?redirect_to=${encodeURIComponent(pathname)}`);
      return;
    }
    if (!roles.includes(user.role)) {
      router.replace(ROLE_HOME[user.role]);
    }
  }, [pathname, user, roles, router]);

  if (!user || !roles.includes(user.role)) {
    return (
      <div className="flex min-h-[50vh] items-center justify-center text-sm text-zinc-500">
        Đang tải...
      </div>
    );
  }

  return <>{children}</>;
}
