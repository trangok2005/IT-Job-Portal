import type {
  AuthTokens,
  GoogleAuthPayload,
  GoogleAuthResponse,
  JobDto,
  LoginPayload,
  Paginated,
  RegisterPayload,
  RegisterResponse,
  UserDto,
} from "@/lib/types";
import type { operations } from "@/types/generated/api-schema";
import { clearAuth, getAccessToken, getRefreshToken, setAccessToken } from "@/lib/auth";

// Server dùng URL nội bộ nếu có; browser dùng URL public.
const BASE_URL = process.env.API_URL
  ?? process.env.NEXT_PUBLIC_API_URL
  ?? "http://localhost:8000";

function getErrorMessage(body: unknown): string | null {
  if (typeof body === "string") return body;
  if (!body || typeof body !== "object") return null;
  for (const value of Object.values(body)) {
    const message = getErrorMessage(value);
    if (message) return message;
  }
  return null;
}

export class ApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

async function readResponse<T>(res: Response, path: string): Promise<T> {
  if (!res.ok) {
    let message = `API ${res.status} on ${path}`;
    try {
      const body = await res.json();
      message = getErrorMessage(body) ?? message;
    } catch {
      // Dùng thông báo HTTP khi body không phải JSON.
    }
    throw new ApiError(res.status, message);
  }
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

function buildHeaders(init: RequestInit, accessToken?: string): Headers {
  const headers = new Headers(init.headers);
  if (typeof init.body === "string" && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  if (accessToken) headers.set("Authorization", `Bearer ${accessToken}`);
  return headers;
}

export async function apiRequest<T>(path: string, init: RequestInit = {}): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    ...init,
    cache: "no-store",
    headers: buildHeaders(init),
  });
  return readResponse<T>(res, path);
}

let refreshInFlight: {
  refresh: string;
  promise: Promise<string | null>;
} | null = null;

function requestAccessToken(): Promise<string | null> {
  const refresh = getRefreshToken();
  if (!refresh) return Promise.resolve(null);

  // Chỉ dùng chung request refresh trong cùng một phiên.
  if (refreshInFlight?.refresh === refresh) return refreshInFlight.promise;

  const promise = fetch(`${BASE_URL}/api/auth/token/refresh/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh }),
    cache: "no-store",
  })
    .then(async (res) => {
      if (res.status === 401 || res.status === 403) return null;
      // Backend lỗi hoặc mất mạng không có nghĩa refresh token đã hết hạn.
      const data = await readResponse<{ access?: string }>(res, "/api/auth/token/refresh/");
      if (!data.access) return null;
      // Không để refresh cũ ghi đè phiên mới hoặc khôi phục phiên đã logout.
      if (getRefreshToken() !== refresh) return null;
      setAccessToken(data.access);
      return data.access;
    });

  refreshInFlight = { refresh, promise };
  const releaseRefresh = () => {
    if (refreshInFlight?.promise === promise) refreshInFlight = null;
  };
  void promise.then(releaseRefresh, releaseRefresh);
  return promise;
}

export async function authApiRequest<T>(path: string, init: RequestInit = {}): Promise<T> {
  let token = getAccessToken();
  const sessionRefresh = getRefreshToken();
  // Khôi phục phiên nếu chỉ thiếu access token.
  token ??= await requestAccessToken();
  if (!token) {
    if (getRefreshToken() === sessionRefresh) clearAuth();
    throw new ApiError(401, "Phiên đăng nhập đã hết hạn. Vui lòng đăng nhập lại.");
  }

  const sendWith = (accessToken: string) => fetch(`${BASE_URL}${path}`, {
    ...init,
    cache: "no-store",
    headers: buildHeaders(init, accessToken),
  });

  let res = await sendWith(token);
  if (res.status === 401) {
    // Dùng token mới nếu request khác đã refresh trước.
    const current = getAccessToken();
    const refreshed = current && current !== token
      ? current
      : await requestAccessToken();
    if (!refreshed) {
      if (getRefreshToken() === sessionRefresh) clearAuth();
      throw new ApiError(401, "Phiên đăng nhập đã hết hạn. Vui lòng đăng nhập lại.");
    }
    res = await sendWith(refreshed);
    if (res.status === 401) {
      if (getAccessToken() === refreshed) clearAuth();
      throw new ApiError(401, "Phiên đăng nhập đã hết hạn. Vui lòng đăng nhập lại.");
    }
  }
  return readResponse<T>(res, path);
}

export async function optionalAuthApiRequest<T>(path: string, init: RequestInit = {}): Promise<T> {
  if (!getAccessToken() && !getRefreshToken()) return apiRequest<T>(path, init);
  try {
    return await authApiRequest<T>(path, init);
  } catch (error) {
    if (!(error instanceof ApiError) || error.status !== 401) throw error;
    return apiRequest<T>(path, init);
  }
}

export type JobListParams = NonNullable<
  operations["jobs_list"]["parameters"]["query"]
>;

export type JobsListResult = Paginated<JobDto> & {
  search_mode?: string;
  search_fallback?: boolean;
};

export function getJobs(params: JobListParams = {}, signal?: AbortSignal): Promise<JobsListResult> {
  const qs = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== null && value !== "") {
      qs.set(key, String(value));
    }
  }
  const query = qs.toString();
  return optionalAuthApiRequest<JobsListResult>(`/api/jobs/${query ? `?${query}` : ""}`, { signal });
}

export function getJob(id: string) {
  return apiRequest<JobDto>(`/api/jobs/${id}/`);
}

export const login = (payload: LoginPayload) =>
  apiRequest<AuthTokens>("/api/auth/token/", { method: "POST", body: JSON.stringify(payload) });

export const register = (payload: RegisterPayload) =>
  apiRequest<RegisterResponse>("/api/accounts/register/", { method: "POST", body: JSON.stringify(payload) });

export const getMe = (accessToken: string) =>
  apiRequest<UserDto>("/api/accounts/me/", {
    headers: { Authorization: `Bearer ${accessToken}` },
  });

export const googleAuth = (payload: GoogleAuthPayload) =>
  apiRequest<GoogleAuthResponse>("/api/auth/google/", {
    method: "POST",
    body: JSON.stringify(payload),
  });
