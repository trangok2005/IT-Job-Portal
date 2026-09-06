"use client";

import {
  createContext,
  useCallback,
  useContext,
  useSyncExternalStore,
} from "react";

import {
  getMe,
  googleAuth as apiGoogleAuth,
  login as apiLogin,
  register as apiRegister,
} from "@/lib/api-client";
import { clearAuth, getStoredUser, persistAuth } from "@/lib/auth";
import type { LoginPayload, RegisterPayload, UserDto } from "@/lib/types";

// --- Tiny external store đọc current user từ localStorage, đọc sync khi mount
// (an toàn cho SSR: server snapshot = null). Tránh setState trong effect. ---
let cachedUser: UserDto | null | undefined;

function getSnapshot(): UserDto | null {
  if (cachedUser === undefined) cachedUser = getStoredUser();
  return cachedUser;
}

function getServerSnapshot(): UserDto | null {
  return null;
}

const listeners = new Set<() => void>();

function subscribe(onStoreChange: () => void) {
  listeners.add(onStoreChange);
  return () => {
    listeners.delete(onStoreChange);
  };
}

function emitChange() {
  cachedUser = getStoredUser();
  listeners.forEach((listener) => listener());
}

interface AuthContextValue {
  user: UserDto | null;
  signIn: (payload: LoginPayload) => Promise<UserDto>;
  signUp: (payload: RegisterPayload) => Promise<UserDto>;
  signOut: () => void;
  signInWithGoogle: (
    idToken: string,
    role?: "CANDIDATE" | "EMPLOYER",
    companyName?: string,
  ) => Promise<UserDto>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const user = useSyncExternalStore(subscribe, getSnapshot, getServerSnapshot);

  const signIn = useCallback(async (payload: LoginPayload) => {
    const tokens = await apiLogin(payload);
    const me = await getMe(tokens.access);
    persistAuth(tokens, me);
    emitChange();
    return me;
  }, []);

  const signUp = useCallback(async (payload: RegisterPayload) => {
    await apiRegister(payload);
    const tokens = await apiLogin({ email: payload.email, password: payload.password });
    const me = await getMe(tokens.access);
    persistAuth(tokens, me);
    emitChange();
    return me;
  }, []);

  const signOut = useCallback(() => {
    clearAuth();
    emitChange();
  }, []);

  const signInWithGoogle = useCallback(
    async (
      idToken: string,
      role: "CANDIDATE" | "EMPLOYER" = "CANDIDATE",
      companyName = "",
    ) => {
      const result = await apiGoogleAuth({
        id_token: idToken,
        role,
        company_name: companyName,
      });
      persistAuth({ access: result.access, refresh: result.refresh }, result.user);
      emitChange();
      return result.user;
    },
    [],
  );

  return (
    <AuthContext.Provider value={{ user, signIn, signUp, signOut, signInWithGoogle }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
