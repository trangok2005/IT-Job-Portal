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
import { clearAuth, getStoredUser, persistAuth, subscribeAuth } from "@/lib/auth";
import type { AuthTokens, LoginPayload, RegisterPayload, UserDto } from "@/lib/types";

function getServerSnapshot(): UserDto | null {
  return null;
}

async function finishAuth(tokens: AuthTokens): Promise<UserDto> {
  const user = await getMe(tokens.access);
  persistAuth(tokens, user);
  return user;
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
  const user = useSyncExternalStore(subscribeAuth, getStoredUser, getServerSnapshot);

  const signIn = useCallback(async (payload: LoginPayload) => {
    const tokens = await apiLogin(payload);
    return finishAuth(tokens);
  }, []);

  const signUp = useCallback(async (payload: RegisterPayload) => {
    await apiRegister(payload);
    const tokens = await apiLogin({ email: payload.email, password: payload.password });
    return finishAuth(tokens);
  }, []);

  const signOut = useCallback(() => {
    clearAuth();
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
