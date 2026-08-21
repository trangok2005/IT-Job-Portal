import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

const ROLE_HOME: Record<string, string> = {
  CANDIDATE: "/jobs",
  EMPLOYER: "/employer",
  ADMIN: "/admin",
};

export function proxy(request: NextRequest) {
  const { pathname } = request.nextUrl;
  const role = request.cookies.get("jp_role")?.value;

  const requiredRole = pathname === "/candidate" || pathname.startsWith("/candidate/")
    ? "CANDIDATE"
    : pathname === "/employer" || pathname.startsWith("/employer/")
      ? "EMPLOYER"
      : pathname === "/admin" || pathname.startsWith("/admin/")
        ? "ADMIN"
        : null;
  const isProtected = Boolean(requiredRole);

  // Optimistic guard: token thật nằm ở localStorage, cookie này chỉ để redirect nhanh.
  if (isProtected && !role) {
    const loginUrl = new URL("/login", request.url);
    loginUrl.searchParams.set("redirect_to", `${pathname}${request.nextUrl.search}`);
    return NextResponse.redirect(loginUrl);
  }

  if (requiredRole && role && role !== requiredRole && ROLE_HOME[role]) {
    return NextResponse.redirect(new URL(ROLE_HOME[role], request.url));
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/candidate/:path*", "/employer/:path*", "/admin/:path*"],
};
