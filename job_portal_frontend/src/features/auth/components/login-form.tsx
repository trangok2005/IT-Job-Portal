"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { AuthForm } from "@/features/auth/components/auth-form";
import { GoogleSignInButton } from "@/features/auth/components/google-sign-in-button";
import { useAuth } from "@/lib/auth-provider";
import { getSafeRedirectPath, POST_LOGIN_HOME } from "@/lib/auth";
import type { UserRole } from "@/lib/types";

export function LoginForm({ redirectTo }: { redirectTo?: string }) {
  const { signIn, signInWithGoogle } = useAuth();
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [googleSubmitting, setGoogleSubmitting] = useState(false);

  const destinationFor = (role: UserRole) =>
    getSafeRedirectPath(redirectTo ?? null) ?? POST_LOGIN_HOME[role];

  const onSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const email = String(form.get("email") ?? "").trim();
    const password = String(form.get("password") ?? "");
    setSubmitting(true);
    setError(null);
    try {
      const user = await signIn({ email, password });
      router.replace(destinationFor(user.role));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Đăng nhập thất bại. Vui lòng thử lại.");
    } finally {
      setSubmitting(false);
    }
  };

  const onGoogleCredential = async (credential: string) => {
    if (googleSubmitting) return;
    setGoogleSubmitting(true);
    setError(null);
    try {
      const user = await signInWithGoogle(credential);
      router.replace(destinationFor(user.role));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Đăng nhập Google thất bại.");
    } finally {
      setGoogleSubmitting(false);
    }
  };

  return (
    <div className="space-y-5">
      {error && (
        <p className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-600">
          {error}
        </p>
      )}

      <AuthForm
        mode="login"
        onSubmit={onSubmit}
        submitting={submitting}
        submitLabel="Đăng nhập"
      />

      <div className="relative">
        <div className="absolute inset-0 flex items-center">
          <span className="w-full border-t border-zinc-200" />
        </div>
        <div className="relative flex justify-center text-xs uppercase text-zinc-400">
          <span className="bg-white px-3">hoặc</span>
        </div>
      </div>

      <GoogleSignInButton
        onCredential={onGoogleCredential}
        disabled={submitting || googleSubmitting}
      />

      <p className="text-center text-sm text-zinc-500">
        Chưa có tài khoản?{" "}
        <Link href="/register" className="font-medium text-primary hover:underline">
          Đăng ký ngay
        </Link>
      </p>
    </div>
  );
}
