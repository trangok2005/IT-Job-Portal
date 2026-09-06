"use client";

import { useRouter, useSearchParams } from "next/navigation";

import { MatchingWeightPanel } from "@/features/admin/components/matching-weight-panel";
import { SkillManagementPanel } from "@/features/admin/components/skill-management-panel";
import type { AdminSkillDto } from "@/features/admin/types";

export type SkillsTab = "catalog" | "aliases" | "pending";

const SKILL_STATUSES: AdminSkillDto["status"][] = [
  "PENDING",
  "APPROVED",
  "REJECTED",
  "MERGED",
];

export function SkillsAdmin() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const rawTab = searchParams.get("tab");
  const tab: SkillsTab = rawTab === "aliases" || rawTab === "pending" ? rawTab : "catalog";
  const rawStatus = searchParams.get("status") as AdminSkillDto["status"] | null;
  const status = tab === "pending"
    ? "PENDING"
    : rawStatus && SKILL_STATUSES.includes(rawStatus) ? rawStatus : "";
  const rawPage = Number(searchParams.get("page"));
  const page = Number.isInteger(rawPage) && rawPage > 0 ? rawPage : 1;

  const updateQuery = (changes: {
    tab?: SkillsTab;
    status?: AdminSkillDto["status"] | "";
    page?: number;
  }) => {
    const nextTab = changes.tab ?? tab;
    const nextStatus = nextTab === "pending" ? "PENDING" : changes.status ?? status;
    const nextPage = changes.page ?? page;
    const next = new URLSearchParams();
    if (nextTab !== "catalog") next.set("tab", nextTab);
    if (nextStatus) next.set("status", nextStatus);
    if (nextPage > 1) next.set("page", String(nextPage));
    router.push(`/admin/skills${next.size ? `?${next}` : ""}`);
  };

  return (
    <div className="mx-auto w-full max-w-7xl px-4 py-8 sm:px-6 sm:py-10 lg:px-8">
      <header>
        <h1 className="text-2xl font-bold tracking-tight text-zinc-900 sm:text-3xl">
          Quản lý kỹ năng và cấu hình trọng số
        </h1>
        <p className="mt-2 max-w-3xl text-sm text-zinc-500 sm:text-base">
          Chuẩn hóa dữ liệu kỹ năng và điều chỉnh tiêu chí tính mức độ phù hợp.
        </p>
      </header>

      <div className="mt-8 grid items-start gap-6 lg:grid-cols-[minmax(0,2fr)_minmax(320px,1fr)]">
        <SkillManagementPanel
          tab={tab}
          status={status}
          page={page}
          onQueryChange={updateQuery}
        />
        <div className="lg:sticky lg:top-24">
          <MatchingWeightPanel />
        </div>
      </div>
    </div>
  );
}
