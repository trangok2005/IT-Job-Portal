"use client";

import { useEffect } from "react";
import { redirect } from "next/navigation";

import { hasAccessCookie, ROLE_HOME } from "@/lib/auth";
import { useAuth } from "@/lib/auth-provider";

export function GuestOnly({ children }: { children: React.ReactNode }) {
  const { user, signOut } = useAuth();
  // Proxy clears invalid cookies but cannot clear localStorage. Requiring both
  // prevents stale local user data from bouncing between login and role home.
  useEffect(() => {
    if (user && !hasAccessCookie()) {
      signOut();
    }
  }, [user, signOut]);
  if (user && hasAccessCookie()) redirect(ROLE_HOME[user.role]);
  return children;
}
