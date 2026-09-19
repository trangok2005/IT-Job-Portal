"use client";

import { useEffect } from "react";

import { hasAccessCookie } from "@/lib/auth";
import { useAuth } from "@/lib/auth-provider";

export function GuestOnly({ children }: { children: React.ReactNode }) {
  const { user, signOut } = useAuth();
  // Đồng bộ localStorage khi Proxy đã xóa cookie không hợp lệ.
  useEffect(() => {
    if (user && !hasAccessCookie()) {
      signOut();
    }
  }, [user, signOut]);
  // Proxy đã xác minh session và redirect user hợp lệ trước khi tới trang này.
  return children;
}
