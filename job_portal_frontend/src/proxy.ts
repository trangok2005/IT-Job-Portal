import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";
import { ROLE_HOME } from "@/lib/auth";
import type { UserDto, UserRole } from "@/lib/types";

const API_URL = process.env.API_URL
  ?? process.env.NEXT_PUBLIC_API_URL
  ?? "http://localhost:8000";
const ACCESS_COOKIE = "jp_access";
const REFRESH_COOKIE = "jp_refresh";
const AUTH_COOKIE_MAX_AGE = 60 * 60 * 24 * 7;
const VALID_ROLES = new Set(["CANDIDATE", "EMPLOYER", "ADMIN"]);

type AuthenticatedUser = Pick<UserDto, "role">;

function isGuestRoute(pathname: string) {
  return pathname === "/login" || pathname === "/register";
}

function getRequiredRole(pathname: string): UserRole | null {
  if (pathname === "/candidate" || pathname.startsWith("/candidate/")) return "CANDIDATE";
  if (pathname === "/employer" || pathname.startsWith("/employer/")) return "EMPLOYER";
  if (pathname === "/admin" || pathname.startsWith("/admin/")) return "ADMIN";
  return null;
}

async function getAuthenticatedUser(access: string): Promise<AuthenticatedUser | null> {
  const response = await fetch(`${API_URL}/api/accounts/me/`, {
    headers: { Authorization: `Bearer ${access}` },
    cache: "no-store",
    signal: AbortSignal.timeout(30000),
  });
  if (response.status === 401 || response.status === 403) return null;
  if (!response.ok) throw new Error(`Authentication API ${response.status}`);
  return await response.json() as AuthenticatedUser;
}

async function refreshAccessToken(refresh: string): Promise<string | null> {
  const response = await fetch(`${API_URL}/api/auth/token/refresh/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh }),
    cache: "no-store",
    signal: AbortSignal.timeout(30000),
  });
  if (response.status === 401 || response.status === 403) return null;
  if (!response.ok) throw new Error(`Refresh API ${response.status}`);
  const data = await response.json() as { access?: string };
  return data.access ?? null;
}

function setRefreshedAccessCookie(
  response: NextResponse,
  request: NextRequest,
  refreshedAccess: string | null,
) {
  const options = {
    path: "/",
    maxAge: AUTH_COOKIE_MAX_AGE,
    sameSite: "lax" as const,
    secure: request.nextUrl.protocol === "https:",
  };
  if (refreshedAccess) {
    response.cookies.set(ACCESS_COOKIE, refreshedAccess, options);
  }
}

function clearAuthCookies(response: NextResponse) {
  response.cookies.delete(ACCESS_COOKIE);
  response.cookies.delete(REFRESH_COOKIE);
}

export async function proxy(request: NextRequest) {
  const { pathname } = request.nextUrl;

  if (pathname === "/candidate/jobs/recommended") {
    return NextResponse.redirect(new URL("/jobs?tab=recommended", request.url));
  }

  const isGuestOnlyRoute = isGuestRoute(pathname);
  const requiredRole = getRequiredRole(pathname);
  if (!isGuestOnlyRoute && !requiredRole) return NextResponse.next();

  const access = request.cookies.get(ACCESS_COOKIE)?.value;
  let user: AuthenticatedUser | null = null;
  let refreshedAccess: string | null = null;

  try {
    user = access ? await getAuthenticatedUser(access) : null;
    if (!user) {
      const refresh = request.cookies.get(REFRESH_COOKIE)?.value;
      if (refresh) {
        refreshedAccess = await refreshAccessToken(refresh);
        if (refreshedAccess) {
          user = await getAuthenticatedUser(refreshedAccess);
        }
      }
    }
  } catch {
    // Chưa xác minh được do backend lỗi: giữ session, không mở route được bảo vệ.
    return new NextResponse("Không thể xác minh phiên đăng nhập. Vui lòng thử lại sau.", {
      status: 503,
      headers: { "Content-Type": "text/plain; charset=utf-8" },
    });
  }

  const role = user?.role;
  if (!role || !VALID_ROLES.has(role)) {
    if (isGuestOnlyRoute) {
      const response = NextResponse.next();
      clearAuthCookies(response);
      return response;
    }
    const loginUrl = new URL("/login", request.url);
    loginUrl.searchParams.set("redirect_to", `${pathname}${request.nextUrl.search}`);
    const response = NextResponse.redirect(loginUrl);
    clearAuthCookies(response);
    return response;
  }

  if (isGuestOnlyRoute || (requiredRole && role !== requiredRole)) {
    const response = NextResponse.redirect(new URL(ROLE_HOME[role], request.url));
    setRefreshedAccessCookie(response, request, refreshedAccess);
    return response;
  }

  const response = NextResponse.next();
  setRefreshedAccessCookie(response, request, refreshedAccess);
  return response;
}

export const config = {
  matcher: ["/login", "/register", "/candidate/:path*", "/employer/:path*", "/admin/:path*"],
};
