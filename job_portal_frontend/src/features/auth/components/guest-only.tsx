"use client";

import { useEffect } from "react";
import { redirect } from "next/navigation";

import { hasAccessCookie, ROLE_HOME } from "@/lib/auth";
import { useAuth } from "@/lib/auth-provider";

export function GuestOnly({ children }: { children: React.ReactNode }) {
  const { user, signOut } = useAuth();
  // Proxy xóa cookie không hợp lệ nhưng không thể xóa localStorage. Việc yêu cầu cả hai
  // ngăn dữ liệu user cục bộ cũ chuyển qua lại giữa trang đăng nhập và trang chủ theo role.
  useEffect(() => {
    if (user && !hasAccessCookie()) {
      signOut();
    }
  }, [user, signOut]);
  if (user && hasAccessCookie()) redirect(ROLE_HOME[user.role]);
  return children;
}
