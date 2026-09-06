"use client";

import { BriefcaseBusiness, UserRound } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { AuthForm } from "@/features/auth/components/auth-form";
import { GoogleSignInButton } from "@/features/auth/components/google-sign-in-button";
import { ROLE_HOME } from "@/lib/auth";
import { useAuth } from "@/lib/auth-provider";

type RegisterRole = "CANDIDATE" | "EMPLOYER";

function splitName(fullName: string) {
  const parts = fullName.trim().split(/\s+/);
  const last_name = parts.pop() ?? "";
  return { first_name: parts.join(" "), last_name };
}

export function RegisterForm({ initialRole = "CANDIDATE" }: { initialRole?: RegisterRole }) {
  const [role, setRole] = useState<RegisterRole>(initialRole);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [companyName, setCompanyName] = useState("");
  const { signUp, signInWithGoogle } = useAuth();
  const router = useRouter();

  const submit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const password = String(form.get("password") ?? "");
    const confirmPassword = String(form.get("confirm_password") ?? "");
    const fullName = String(form.get("full_name") ?? "").trim();
    const email = String(form.get("email") ?? "").trim();
    if (password.length < 8) return setError("Mật khẩu tối thiểu 8 ký tự.");
    if (password !== confirmPassword) return setError("Mật khẩu xác nhận không khớp.");
    if (role === "EMPLOYER" && !companyName.trim()) return setError("Vui lòng nhập tên công ty.");
    setSubmitting(true);
    setError(null);
    try {
      const names = splitName(fullName);
      const user = await signUp({
        email,
        username: email,
        password,
        role,
        ...names,
        company_name: role === "EMPLOYER" ? companyName.trim() : undefined,
      });
      router.push(ROLE_HOME[user.role]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Không thể đăng ký tài khoản.");
    } finally {
      setSubmitting(false);
    }
  };

  const googleCredential = async (credential: string) => {
    if (role === "EMPLOYER" && !companyName.trim()) {
      setError("Nhập tên công ty trước khi tiếp tục với Google.");
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      const user = await signInWithGoogle(credential, role, companyName.trim());
      router.push(ROLE_HOME[user.role]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Đăng ký Google thất bại.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="w-full max-w-xl rounded-xl border border-zinc-200 bg-white p-5 shadow-sm sm:p-7">
      <div className="text-center">
        <h1 className="text-2xl font-bold text-zinc-900">Tạo tài khoản</h1>
        <p className="mt-1 text-sm text-zinc-500">Một tài khoản, đúng trải nghiệm cho vai trò của bạn.</p>
      </div>
      <div className="mt-6 grid grid-cols-2 rounded-xl bg-zinc-100 p-1">
        {([
          ["CANDIDATE", UserRound, "Ứng viên"],
          ["EMPLOYER", BriefcaseBusiness, "Nhà tuyển dụng"],
        ] as const).map(([value, Icon, label]) => (
          <button
            key={value}
            type="button"
            onClick={() => setRole(value)}
            className={`flex items-center justify-center gap-2 rounded-lg px-3 py-2.5 text-sm font-medium transition ${role === value ? "bg-white text-primary shadow-sm" : "text-zinc-500"}`}
          >
            <Icon className="size-4" />{label}
          </button>
        ))}
      </div>
      {error && <p className="mt-5 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-600">{error}</p>}
      <div className="mt-5">
        <AuthForm
          mode="register"
          onSubmit={submit}
          submitting={submitting}
          submitLabel={`Đăng ký ${role === "CANDIDATE" ? "ứng viên" : "nhà tuyển dụng"}`}
        >
        <div>
          <Label htmlFor="register-name">{role === "EMPLOYER" ? "Người liên hệ" : "Họ và tên"}</Label>
          <Input id="register-name" name="full_name" className="mt-1.5" required />
        </div>
        {role === "EMPLOYER" && (
          <div>
            <Label htmlFor="register-company">Tên công ty</Label>
            <Input id="register-company" value={companyName} onChange={(event) => setCompanyName(event.target.value)} className="mt-1.5" required />
          </div>
        )}
        </AuthForm>
      </div>
      <div className="relative my-5"><div className="border-t border-zinc-200" /><span className="absolute left-1/2 top-0 -translate-x-1/2 -translate-y-1/2 bg-white px-3 text-xs text-zinc-400">hoặc</span></div>
      <GoogleSignInButton onCredential={googleCredential} disabled={submitting} />
      <p className="mt-5 text-center text-sm text-zinc-500">Đã có tài khoản? <Link href="/login" className="font-medium text-primary">Đăng nhập</Link></p>
    </div>
  );
}
