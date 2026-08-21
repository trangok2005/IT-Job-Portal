"use client";

import { Building2, ExternalLink, MapPin } from "lucide-react";
import { useEffect, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  approveCompany,
  getAdminCompanies,
  lockCompany,
  rejectCompany,
} from "@/features/admin/api";
import type { AdminCompanyQuery, CompanyDto } from "@/features/admin/types";

export function CompaniesAdmin() {
  const [items, setItems] = useState<CompanyDto[]>([]);
  const [filter, setFilter] = useState<AdminCompanyQuery["status"] | "">("PENDING");
  const [loading, setLoading] = useState(true);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = async (status = filter) => {
    setError(null);
    try {
      const response = await getAdminCompanies({ status: status || undefined });
      setItems(response.results);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Không thể tải công ty.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    getAdminCompanies({ status: "PENDING" })
      .then((response) => setItems(response.results))
      .catch((reason: unknown) => {
        setError(reason instanceof Error ? reason.message : "Không thể tải công ty.");
      })
      .finally(() => setLoading(false));
  }, []);

  const act = async (company: CompanyDto, action: "approve" | "reject" | "lock") => {
    let reason = "";
    if (action === "reject") {
      reason = window.prompt("Nhập lý do từ chối hồ sơ công ty:")?.trim() ?? "";
      if (!reason) return;
    } else if (!window.confirm(`Xác nhận ${action === "approve" ? "duyệt" : "khóa"} ${company.name}?`)) {
      return;
    }

    setBusyId(company.id);
    setError(null);
    try {
      if (action === "approve") await approveCompany(company.id);
      if (action === "reject") await rejectCompany(company.id, reason);
      if (action === "lock") await lockCompany(company.id);
      await load();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Không thể cập nhật công ty.");
    } finally {
      setBusyId(null);
    }
  };

  return (
    <div className="mx-auto max-w-6xl px-4 py-7 sm:px-6 lg:px-8">
      <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-end">
        <div>
          <p className="text-sm font-semibold uppercase tracking-[0.18em] text-accent">Verification queue</p>
          <h1 className="mt-2 text-2xl font-bold text-zinc-900">Duyệt hồ sơ công ty</h1>
          <p className="mt-1 text-sm text-zinc-500">Kiểm tra pháp nhân trước khi cho phép đăng tin.</p>
        </div>
        <select
          value={filter}
          onChange={(event) => {
            const value = event.target.value as typeof filter;
            setFilter(value);
            setLoading(true);
            void load(value);
          }}
          className="h-10 rounded-xl border border-zinc-300 bg-white px-3 text-sm"
        >
          <option value="">Tất cả trạng thái</option>
          <option value="PENDING">Chờ duyệt</option>
          <option value="APPROVED">Đã duyệt</option>
          <option value="REJECTED">Từ chối</option>
          <option value="LOCKED">Đã khóa</option>
        </select>
      </div>

      {error && <p className="mt-4 rounded-xl bg-red-50 p-4 text-sm text-red-700">{error}</p>}
      {loading && <div className="mt-6 h-48 animate-pulse rounded-xl bg-zinc-100" />}
      {!loading && items.length === 0 && (
        <p className="mt-6 rounded-xl border border-dashed border-zinc-300 p-12 text-center text-sm text-zinc-500">
          Không có hồ sơ công ty trong trạng thái này.
        </p>
      )}

      {!loading && (
        <div className="mt-6 grid gap-4 lg:grid-cols-2">
          {items.map((company) => (
            <article key={company.id} className="rounded-xl border border-zinc-200 bg-white p-5 shadow-sm">
              <div className="flex items-start gap-3">
                <span className="grid size-11 shrink-0 place-items-center rounded-xl bg-primary-50 text-primary">
                  <Building2 className="size-5" />
                </span>
                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <h2 className="font-semibold text-zinc-900">{company.name}</h2>
                    <Badge variant={company.status === "APPROVED" ? "success" : "outline"}>
                      {company.status}
                    </Badge>
                  </div>
                  <p className="mt-1 text-sm text-zinc-500">{company.owner_email}</p>
                </div>
              </div>

              <dl className="mt-4 grid grid-cols-2 gap-3 rounded-xl bg-zinc-50 p-3 text-xs">
                <div><dt className="text-zinc-400">Mã số thuế</dt><dd className="mt-1 font-medium text-zinc-700">{company.tax_code || "Chưa có"}</dd></div>
                <div><dt className="text-zinc-400">Quy mô</dt><dd className="mt-1 font-medium text-zinc-700">{company.company_size || "Chưa có"}</dd></div>
                <div><dt className="text-zinc-400">Ngành</dt><dd className="mt-1 font-medium text-zinc-700">{company.industry || "Chưa có"}</dd></div>
                <div><dt className="text-zinc-400">Ngày gửi</dt><dd className="mt-1 font-medium text-zinc-700">{new Date(company.created_at).toLocaleDateString("vi-VN")}</dd></div>
              </dl>

              <p className="mt-4 line-clamp-3 text-sm leading-6 text-zinc-600">{company.description || "Chưa có mô tả."}</p>
              {company.address && <p className="mt-3 flex items-center gap-2 text-xs text-zinc-500"><MapPin className="size-3.5" />{company.address}</p>}
              {company.website && <a href={company.website} target="_blank" rel="noreferrer" className="mt-2 inline-flex items-center gap-1 text-xs font-medium text-primary hover:underline">Website <ExternalLink className="size-3" /></a>}
              {company.rejection_reason && <p className="mt-3 rounded-lg bg-amber-50 p-3 text-xs text-amber-800">Lý do: {company.rejection_reason}</p>}

              <div className="mt-4 flex flex-wrap justify-end gap-2 border-t border-zinc-100 pt-4">
                {company.status === "PENDING" && (
                  <>
                    <Button size="sm" variant="outline" disabled={busyId === company.id} onClick={() => void act(company, "reject")}>Từ chối</Button>
                    <Button size="sm" disabled={busyId === company.id} onClick={() => void act(company, "approve")}>Duyệt công ty</Button>
                  </>
                )}
                {company.status === "APPROVED" && <Button size="sm" variant="outline" disabled={busyId === company.id} onClick={() => void act(company, "lock")}>Khóa công ty</Button>}
              </div>
            </article>
          ))}
        </div>
      )}
    </div>
  );
}
