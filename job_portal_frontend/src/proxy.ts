import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

const API_URL = process.env.API_URL
  ?? process.env.NEXT_PUBLIC_API_URL
  ?? "http://localhost:8000";
const ACCESS_COOKIE = "jp_access";
const REFRESH_COOKIE = "jp_refresh";
const ROLE_COOKIE = "jp_role";
const AUTH_COOKIE_MAX_AGE = 60 * 60 * 24 * 7;
const VALID_ROLES = new Set(["CANDIDATE", "EMPLOYER", "ADMIN"]);

const ROLE_HOME: Record<string, string> = {
  CANDIDATE: "/jobs",
  EMPLOYER: "/employer",
  ADMIN: "/admin",
};

type AuthenticatedUser = {
  role?: string;
};

async function getAuthenticatedUser(access: string): Promise<AuthenticatedUser | null> {
  try {
    const response = await fetch(`${API_URL}/api/accounts/me/`, {
      headers: { Authorization: `Bearer ${access}` },
      cache: "no-store",
      signal: AbortSignal.timeout(30000),
    });
    if (!response.ok) return null;
    return await response.json() as AuthenticatedUser;
  } catch {
    return null;
  }
}

async function refreshAccessToken(refresh: string): Promise<string | null> {
  try {
    const response = await fetch(`${API_URL}/api/auth/token/refresh/`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh }),
      cache: "no-store",
      signal: AbortSignal.timeout(30000),
    });
    if (!response.ok) return null;
    const data = await response.json() as { access?: string };
    return data.access ?? null;
  } catch {
    return null;
  }
}

function setVerifiedCookies(
  response: NextResponse,
  request: NextRequest,
  role: string,
  refreshedAccess: string | null,
) {
  const options = {
    path: "/",
    maxAge: AUTH_COOKIE_MAX_AGE,
    sameSite: "lax" as const,
    secure: request.nextUrl.protocol === "https:",
  };
  response.cookies.set(ROLE_COOKIE, role, options);
  if (refreshedAccess) {
    response.cookies.set(ACCESS_COOKIE, refreshedAccess, options);
  }
}

function clearAuthCookies(response: NextResponse) {
  response.cookies.delete(ACCESS_COOKIE);
  response.cookies.delete(REFRESH_COOKIE);
  response.cookies.delete(ROLE_COOKIE);
}

export async function proxy(request: NextRequest) {
  const { pathname } = request.nextUrl;
  const isGuestOnlyRoute = pathname === "/login" || pathname === "/register";

  if (pathname === "/candidate/jobs/recommended") {
    return NextResponse.redirect(new URL("/jobs?tab=recommended", request.url));
  }

  const requiredRole = pathname === "/candidate" || pathname.startsWith("/candidate/")
    ? "CANDIDATE"
    : pathname === "/employer" || pathname.startsWith("/employer/")
      ? "EMPLOYER"
      : pathname === "/admin" || pathname.startsWith("/admin/")
        ? "ADMIN"
        : null;

  let access = request.cookies.get(ACCESS_COOKIE)?.value ?? null;
  let user = access ? await getAuthenticatedUser(access) : null;
  let refreshedAccess: string | null = null;

  if (!user) {
    const refresh = request.cookies.get(REFRESH_COOKIE)?.value;
    if (refresh) {
      refreshedAccess = await refreshAccessToken(refresh);
      if (refreshedAccess) {
        access = refreshedAccess;
        user = await getAuthenticatedUser(access);
      }
    }
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

  if (isGuestOnlyRoute) {
    const response = NextResponse.redirect(new URL(ROLE_HOME[role], request.url));
    setVerifiedCookies(response, request, role, refreshedAccess);
    return response;
  }

  if (requiredRole && role !== requiredRole) {
    const response = NextResponse.redirect(new URL(ROLE_HOME[role], request.url));
    setVerifiedCookies(response, request, role, refreshedAccess);
    return response;
  }

  const response = NextResponse.next();
  setVerifiedCookies(response, request, role, refreshedAccess);
  return response;
}

export const config = {
  matcher: ["/login", "/register", "/candidate/:path*", "/employer/:path*", "/admin/:path*"],
};
