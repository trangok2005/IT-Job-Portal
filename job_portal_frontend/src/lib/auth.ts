import type { AuthTokens, UserDto, UserRole } from "@/lib/types";

const ACCESS_KEY = "job_portal_access";
const REFRESH_KEY = "job_portal_refresh";
const USER_KEY = "job_portal_user";
const ACCESS_COOKIE = "jp_access";
const REFRESH_COOKIE = "jp_refresh";
const PENDING_APPLICATION_KEY = "job_portal_pending_application";
const AUTH_COOKIE_MAX_AGE = 60 * 60 * 24 * 7;

export const ROLE_HOME: Record<UserRole, string> = {
  CANDIDATE: "/jobs",
  EMPLOYER: "/employer",
  ADMIN: "/admin",
};

let cachedUserRaw: string | null = null;
let cachedUser: UserDto | null = null;
const listeners = new Set<() => void>();

function notifyAuthChange() {
  listeners.forEach((listener) => listener());
}

export function subscribeAuth(listener: () => void) {
  listeners.add(listener);
  // Storage event chỉ chạy ở tab khác; các helper notify ngay trong tab hiện tại.
  const handleStorage = (event: StorageEvent) => {
    if (
      event.storageArea === window.localStorage &&
      (event.key === null || [ACCESS_KEY, REFRESH_KEY, USER_KEY].includes(event.key))
    ) {
      listener();
    }
  };
  window.addEventListener("storage", handleStorage);
  return () => {
    listeners.delete(listener);
    window.removeEventListener("storage", handleStorage);
  };
}

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

export function getAccessToken(): string | null {
  if (typeof window === "undefined") return null;
  const storedAccess = window.localStorage.getItem(ACCESS_KEY);
  const cookieAccess = getAuthCookie(ACCESS_COOKIE);
  const refresh = getRefreshToken();
  // Proxy chỉ ghi được cookie. Nhận lại access mới trước request browser, cùng phiên refresh.
  if (
    refresh &&
    cookieAccess &&
    cookieAccess !== storedAccess &&
    getAuthCookie(REFRESH_COOKIE) === refresh
  ) {
    setAccessToken(cookieAccess);
    return cookieAccess;
  }
  return storedAccess;
}

export const getRefreshToken = (): string | null =>
  typeof window === "undefined" ? null : window.localStorage.getItem(REFRESH_KEY);

export function hasAccessCookie(): boolean {
  return getAuthCookie(ACCESS_COOKIE) !== null;
}

function getAuthCookie(name: string): string | null {
  if (typeof document === "undefined") return null;
  const prefix = `${name}=`;
  const cookie = document.cookie.split("; ").find((item) => item.startsWith(prefix));
  return cookie ? cookie.slice(prefix.length) : null;
}

export function getStoredUser(): UserDto | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = window.localStorage.getItem(USER_KEY);
    // Snapshot giữ nguyên reference để useSyncExternalStore không render lặp.
    if (raw !== cachedUserRaw) {
      cachedUser = raw ? (JSON.parse(raw) as UserDto) : null;
      cachedUserRaw = raw;
    }
    return cachedUser;
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
  notifyAuthChange();
}

export function setAccessToken(accessToken: string) {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(ACCESS_KEY, accessToken);
  setAuthCookie(ACCESS_COOKIE, accessToken);
  notifyAuthChange();
}

export function clearAuth() {
  if (typeof window === "undefined") return;
  window.localStorage.removeItem(ACCESS_KEY);
  window.localStorage.removeItem(REFRESH_KEY);
  window.localStorage.removeItem(USER_KEY);
  clearAuthCookie(ACCESS_COOKIE);
  clearAuthCookie(REFRESH_COOKIE);
  notifyAuthChange();
}

function setAuthCookie(name: string, value: string) {
  const secure = window.location.protocol === "https:" ? "; secure" : "";
  document.cookie = `${name}=${value}; path=/; max-age=${AUTH_COOKIE_MAX_AGE}; samesite=lax${secure}`;
}

function clearAuthCookie(name: string) {
  document.cookie = `${name}=; path=/; max-age=0; samesite=lax`;
}
