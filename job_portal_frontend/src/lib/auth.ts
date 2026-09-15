import type { AuthTokens, UserDto, UserRole } from "@/lib/types";

const ACCESS_KEY = "job_portal_access";
const REFRESH_KEY = "job_portal_refresh";
const USER_KEY = "job_portal_user";
const ACCESS_COOKIE = "jp_access";
const REFRESH_COOKIE = "jp_refresh";
const ROLE_COOKIE = "jp_role";
const PENDING_APPLICATION_KEY = "job_portal_pending_application";
const AUTH_COOKIE_MAX_AGE = 60 * 60 * 24 * 7;

export const ROLE_HOME: Record<UserRole, string> = {
  CANDIDATE: "/jobs",
  EMPLOYER: "/employer",
  ADMIN: "/admin",
};

export const POST_LOGIN_HOME: Record<UserRole, string> = {
  ...ROLE_HOME,
};

export function getSafeRedirectPath(value: string | null): string | null {
  if (!value || !value.startsWith("/") || value.startsWith("//")) return null;
  try {
    const base = new URL("https://job-portal.local");
    const destination = new URL(value, base);
    if (destination.origin !== base.origin) return null;
    return `${destination.pathname}${destination.search}${destination.hash}`;
  } catch {
    return null;
  }
}

export function rememberPendingApplication(jobId: string) {
  if (typeof window === "undefined") return;
  window.sessionStorage.setItem(PENDING_APPLICATION_KEY, jobId);
}

export function consumePendingApplication(jobId: string): boolean {
  if (typeof window === "undefined") return false;
  if (window.sessionStorage.getItem(PENDING_APPLICATION_KEY) !== jobId) return false;
  window.sessionStorage.removeItem(PENDING_APPLICATION_KEY);
  return true;
}

export const getAccessToken = (): string | null =>
  typeof window === "undefined" ? null : window.localStorage.getItem(ACCESS_KEY);

export const getRefreshToken = (): string | null =>
  typeof window === "undefined" ? null : window.localStorage.getItem(REFRESH_KEY);

export function hasAccessCookie(): boolean {
  if (typeof document === "undefined") return false;
  return document.cookie.split("; ").some((cookie) => cookie.startsWith(`${ACCESS_COOKIE}=`));
}

export function getStoredUser(): UserDto | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = window.localStorage.getItem(USER_KEY);
    return raw ? (JSON.parse(raw) as UserDto) : null;
  } catch {
    return null;
  }
}

export function persistAuth(tokens: AuthTokens, user: UserDto) {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(ACCESS_KEY, tokens.access);
  window.localStorage.setItem(REFRESH_KEY, tokens.refresh);
  window.localStorage.setItem(USER_KEY, JSON.stringify(user));
  setAuthCookie(ACCESS_COOKIE, tokens.access);
  setAuthCookie(REFRESH_COOKIE, tokens.refresh);
  setRoleCookie(user.role);
}

export function setAccessToken(accessToken: string) {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(ACCESS_KEY, accessToken);
  setAuthCookie(ACCESS_COOKIE, accessToken);
}

export function clearAuth() {
  if (typeof window === "undefined") return;
  window.localStorage.removeItem(ACCESS_KEY);
  window.localStorage.removeItem(REFRESH_KEY);
  window.localStorage.removeItem(USER_KEY);
  clearAuthCookie(ACCESS_COOKIE);
  clearAuthCookie(REFRESH_COOKIE);
  clearRoleCookie();
}

function setAuthCookie(name: string, value: string) {
  const secure = window.location.protocol === "https:" ? "; secure" : "";
  document.cookie = `${name}=${value}; path=/; max-age=${AUTH_COOKIE_MAX_AGE}; samesite=lax${secure}`;
}

function clearAuthCookie(name: string) {
  document.cookie = `${name}=; path=/; max-age=0; samesite=lax`;
}

// Proxy xác minh role qua backend; cookie chỉ hỗ trợ UX cũ.
export function setRoleCookie(role: UserRole) {
  setAuthCookie(ROLE_COOKIE, role);
}

export function clearRoleCookie() {
  clearAuthCookie(ROLE_COOKIE);
}
