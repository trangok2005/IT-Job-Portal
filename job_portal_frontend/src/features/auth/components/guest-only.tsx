"use client";

import { useEffect } from "react";
import { redirect } from "next/navigation";

import { hasAccessCookie, ROLE_HOME } from "@/lib/auth";
import { useAuth } from "@/lib/auth-provider";

export function GuestOnly({ children }: { children: React.ReactNode }) {
  const { user, signOut } = useAuth();
  // Đồng bộ localStorage khi Proxy đã xóa cookie không hợp lệ.
  useEffect(() => {
    if (user && !hasAccessCookie()) {
      signOut();
    }
  }, [user, signOut]);
  if (user && hasAccessCookie()) redirect(ROLE_HOME[user.role]);
  return children;
}
