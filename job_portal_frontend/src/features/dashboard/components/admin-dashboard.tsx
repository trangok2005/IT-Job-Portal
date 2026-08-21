"use client";

import {
  BriefcaseBusiness,
  Building2,
  Sparkles,
  UsersRound,
} from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";

import { getAdminDashboard } from "@/features/dashboard/api";
import type { AdminDashboardDto } from "@/features/dashboard/types";

export function AdminDashboard() {
  const [data, setData] = useState<AdminDashboardDto | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getAdminDashboard()
      .then(setData)
      .catch((reason: unknown) => {
        setError(reason instanceof Error ? reason.message : "Không thể tải dashboard.");
      });
  }, []);

  if (error) {
    return (
      <div className="mx-auto max-w-6xl px-4 py-8 sm:px-6 lg:px-8">
        <p className="rounded-xl border border-red-100 bg-red-50 p-4 text-sm text-red-700">
          {error}
        </p>
      </div>
    );
  }

  if (!data) {
    return <div className="mx-auto mt-8 h-64 max-w-6xl animate-pulse rounded-xl bg-zinc-100" />;
  }

  const stats = [
    ["Người dùng", data.users_total, UsersRound, "/admin/users"],
    ["Công ty chờ duyệt", data.pending_companies, Building2, "/admin/companies"],
    ["Job đang chạy", data.active_jobs, BriefcaseBusiness, "/jobs"],
    ["Skill chờ duyệt", data.pending_skills, Sparkles, "/admin/skills"],
  ] as const;

  return (
    <div className="mx-auto max-w-6xl px-4 py-7 sm:px-6 lg:px-8">
      <p className="text-sm font-semibold uppercase tracking-[0.2em] text-accent">System control</p>
      <h1 className="mt-2 text-3xl font-bold text-zinc-900">Dashboard quản trị</h1>
      <p className="mt-1 text-sm text-zinc-500">Theo dõi sức khỏe và hàng đợi kiểm duyệt.</p>
      <div className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {stats.map(([label, value, Icon, href]) => (
          <Link
            key={label}
            href={href}
            className="group rounded-xl border border-zinc-200 bg-white p-5 shadow-sm transition hover:-translate-y-0.5 hover:border-primary-200 hover:shadow-md"
          >
            <span className="grid size-10 place-items-center rounded-xl bg-primary-50 text-primary transition group-hover:bg-primary group-hover:text-white">
              <Icon className="size-5" />
            </span>
            <p className="mt-4 text-2xl font-bold text-zinc-900">{value}</p>
            <p className="mt-1 text-sm text-zinc-500">{label}</p>
          </Link>
        ))}
      </div>
      <div className="mt-6 rounded-xl border border-zinc-200 bg-white p-5 text-sm text-zinc-600 shadow-sm">
        Tổng hồ sơ ứng tuyển: <strong className="text-primary">{data.applications}</strong>
        <span className="mx-2 text-zinc-300">/</span>
        Tài khoản hoạt động: <strong className="text-primary">{data.users_active}</strong>
      </div>
    </div>
  );
}
