"use client";

import { Loader2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

interface AuthFormProps {
  mode: "login" | "register";
  onSubmit: (event: React.FormEvent<HTMLFormElement>) => void;
  submitting: boolean;
  submitLabel: string;
  children?: React.ReactNode;
  afterFields?: React.ReactNode;
}

export function AuthForm({
  mode,
  onSubmit,
  submitting,
  submitLabel,
  children,
  afterFields,
}: AuthFormProps) {
  const registering = mode === "register";

  return (
    <form onSubmit={onSubmit} className="space-y-5">
      {children}
      <div className={registering ? "grid gap-4 sm:grid-cols-2" : "space-y-5"}>
        <div className="space-y-2">
          <Label htmlFor={`${mode}-email`}>Email</Label>
          <Input
            id={`${mode}-email`}
            name="email"
            type="email"
            autoComplete="email"
            placeholder="you@example.com"
            required
          />
        </div>
        <div className="space-y-2">
          <Label htmlFor={`${mode}-password`}>Mật khẩu</Label>
          <Input
            id={`${mode}-password`}
            name="password"
            type="password"
            autoComplete={registering ? "new-password" : "current-password"}
            placeholder={registering ? "Tối thiểu 8 ký tự" : "Nhập mật khẩu"}
            minLength={8}
            required
          />
        </div>
        {registering && (
          <div className="space-y-2 sm:col-start-2">
            <Label htmlFor="register-confirm-password">Xác nhận mật khẩu</Label>
            <Input
              id="register-confirm-password"
              name="confirm_password"
              type="password"
              autoComplete="new-password"
              placeholder="Nhập lại mật khẩu"
              minLength={8}
              required
            />
          </div>
        )}
      </div>
      {afterFields}
      <Button type="submit" size="lg" className="w-full" disabled={submitting}>
        {submitting && <Loader2 className="h-4 w-4 animate-spin" />}
        {submitLabel}
      </Button>
    </form>
  );
}
