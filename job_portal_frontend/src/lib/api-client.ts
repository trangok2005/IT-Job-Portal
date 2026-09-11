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

// Server Components trong Docker dùng tên service nội bộ; request từ browser
// tiếp tục dùng host URL công khai được build vào NEXT_PUBLIC_API_URL.
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
      // Giữ HTTP fallback khi body lỗi không phải JSON hợp lệ.
    }
    throw new ApiError(res.status, message);
  }
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

export async function apiRequest<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  if (!(init.body instanceof FormData) && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  const res = await fetch(`${BASE_URL}${path}`, {
    ...init,
    cache: "no-store",
    headers,
  });
  return readResponse<T>(res, path);
}

let refreshInFlight: {
  refresh: string;
  promise: Promise<string | null>;
} | null = null;

/** Dùng refresh token đổi access token mới. Trả null nếu không refresh được. */
function requestAccessToken(): Promise<string | null> {
  const refresh = getRefreshToken();
  if (!refresh) return Promise.resolve(null);

  // Gom các request cùng phiên vào một lần refresh. Phiên mới không chờ
  // promise của phiên cũ (tránh logout/login trong lúc request đang chạy).
  if (refreshInFlight?.refresh === refresh) return refreshInFlight.promise;

  const promise = fetch(`${BASE_URL}/api/auth/token/refresh/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh }),
    cache: "no-store",
  })
    .then(async (res) => {
      if (!res.ok) return null;
      const data = (await res.json()) as { access?: string };
      if (!data.access) return null;
      // Không cho refresh cũ khôi phục phiên đã logout hoặc ghi đè user mới.
      if (getRefreshToken() !== refresh) return null;
      setAccessToken(data.access);
      return data.access;
    })
    .catch(() => null);

  refreshInFlight = { refresh, promise };
  void promise.finally(() => {
    if (refreshInFlight?.promise === promise) refreshInFlight = null;
  });
  return promise;
}

export async function authApiRequest<T>(path: string, init: RequestInit = {}): Promise<T> {
  let token = getAccessToken();
  const sessionRefresh = getRefreshToken();
  // Access hết hạn từ phiên trước nhưng refresh còn hạn -> tự phục hồi ngay.
  token ??= await requestAccessToken();
  if (!token) {
    if (getRefreshToken() === sessionRefresh) clearAuth();
    throw new ApiError(401, "Phiên đăng nhập đã hết hạn. Vui lòng đăng nhập lại.");
  }

  const sendWith = (accessToken: string) => {
    const headers = new Headers(init.headers);
    headers.set("Authorization", `Bearer ${accessToken}`);
    if (!(init.body instanceof FormData) && !headers.has("Content-Type")) {
      headers.set("Content-Type", "application/json");
    }
    return fetch(`${BASE_URL}${path}`, { ...init, cache: "no-store", headers });
  };

  let res = await sendWith(token);
  if (res.status === 401) {
    // Một request khác có thể đã refresh trong lúc request này đang bay.
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

const request = apiRequest;

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
  return request<JobDto>(`/api/jobs/${id}/`);
}

export const login = (payload: LoginPayload) =>
  request<AuthTokens>("/api/auth/token/", { method: "POST", body: JSON.stringify(payload) });

export const register = (payload: RegisterPayload) =>
  request<RegisterResponse>("/api/accounts/register/", { method: "POST", body: JSON.stringify(payload) });

export const getMe = (accessToken: string) =>
  request<UserDto>("/api/accounts/me/", {
    headers: { Authorization: `Bearer ${accessToken}` },
  });

export const googleAuth = (payload: GoogleAuthPayload) =>
  request<GoogleAuthResponse>("/api/auth/google/", {
    method: "POST",
    body: JSON.stringify(payload),
  });
