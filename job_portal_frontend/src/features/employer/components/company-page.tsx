"use client";

import { Building2, Loader2, RotateCcw } from "lucide-react";
import { useEffect, useRef, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { getMyCompany, resubmitCompany, updateMyCompany } from "@/features/employer/api";
import type { CompanyDto, CompanyUpdatePayload } from "@/features/employer/types";

export function CompanyPage() {
  const formRef = useRef<HTMLFormElement>(null);
  const [company, setCompany] = useState<CompanyDto | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      setCompany(await getMyCompany());
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Không thể tải hồ sơ công ty.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    getMyCompany()
      .then(setCompany)
      .catch((reason: unknown) => setError(reason instanceof Error ? reason.message : "Không thể tải hồ sơ công ty."))
      .finally(() => setLoading(false));
  }, []);

  const payloadFrom = (form: HTMLFormElement): CompanyUpdatePayload => {
    const data = new FormData(form);
    return {
      name: String(data.get("name") ?? "").trim(),
      tax_code: String(data.get("tax_code") ?? "").trim() || null,
      industry: String(data.get("industry") ?? "").trim(),
      company_size: String(data.get("company_size") ?? "").trim(),
      website: String(data.get("website") ?? "").trim(),
      logo_url: String(data.get("logo_url") ?? "").trim(),
      address: String(data.get("address") ?? "").trim(),
      description: String(data.get("description") ?? "").trim(),
    };
  };

  const save = async (form: HTMLFormElement) => {
    const updated = await updateMyCompany(payloadFrom(form));
    setCompany(updated);
    return updated;
  };

  const submit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setSaving(true);
    setMessage(null);
    setError(null);
    try {
      await save(event.currentTarget);
      setMessage("Đã cập nhật hồ sơ công ty.");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Không thể cập nhật hồ sơ.");
    } finally {
      setSaving(false);
    }
  };

  const resubmit = async () => {
    if (!company || !formRef.current) return;
    setSaving(true);
    setMessage(null);
    setError(null);
    try {
      const updated = await save(formRef.current);
      setCompany(await resubmitCompany(updated.id));
      setMessage("Đã lưu thay đổi và gửi lại hồ sơ để Admin xét duyệt.");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Không thể gửi lại hồ sơ.");
    } finally {
      setSaving(false);
    }
  };

  if (loading) return <div className="mx-auto mt-8 h-72 max-w-4xl animate-pulse rounded-xl bg-zinc-100" />;
  if (!company) return <div className="mx-auto max-w-3xl px-4 py-12 text-center"><p className="rounded-xl bg-red-50 p-4 text-sm text-red-700">{error ?? "Chưa có hồ sơ công ty."}</p><Button variant="outline" className="mt-4" onClick={() => void load()}><RotateCcw />Thử lại</Button></div>;

  return (
    <div className="mx-auto max-w-4xl px-4 py-7 sm:px-6 lg:px-8">
      <div className="flex items-center gap-3">
        <span className="grid size-11 place-items-center rounded-xl bg-primary-50 text-primary"><Building2 /></span>
        <div><h1 className="text-2xl font-bold text-zinc-900">Hồ sơ công ty</h1><p className="text-sm text-zinc-500">Thông tin xác thực trước khi đăng tin.</p></div>
        <Badge className="ml-auto" variant={company.status === "APPROVED" ? "success" : company.status === "REJECTED" ? "accent" : "outline"}>{company.status}</Badge>
      </div>
      {company.rejection_reason && <div className="mt-5 rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-800"><strong>Lý do:</strong> {company.rejection_reason}</div>}
      {message && <p className="mt-5 rounded-xl bg-emerald-50 p-4 text-sm text-emerald-700">{message}</p>}
      {error && <p className="mt-5 rounded-xl bg-red-50 p-4 text-sm text-red-700">{error}</p>}

      <form ref={formRef} onSubmit={submit} className="mt-6 space-y-5 rounded-xl border border-zinc-200 bg-white p-5 shadow-sm sm:p-7">
        <div className="grid gap-4 sm:grid-cols-2">
          <CompanyField name="name" label="Tên công ty" value={company.name} required />
          <CompanyField name="tax_code" label="Mã số thuế" value={company.tax_code ?? ""} />
          <CompanyField name="industry" label="Lĩnh vực" value={company.industry} />
          <CompanyField name="company_size" label="Quy mô" value={company.company_size} />
          <CompanyField name="website" label="Website" value={company.website} />
          <CompanyField name="logo_url" label="Logo URL" value={company.logo_url} />
          <div className="sm:col-span-2"><CompanyField name="address" label="Địa chỉ" value={company.address} /></div>
        </div>
        <label className="block"><span className="text-sm font-medium text-zinc-700">Giới thiệu</span><textarea name="description" defaultValue={company.description} className="mt-1.5 min-h-36 w-full rounded-xl border border-zinc-300 p-3.5 text-sm outline-none focus:border-primary" /></label>
        <div className="flex flex-col gap-2 border-t border-zinc-100 pt-5 sm:flex-row sm:justify-end">
          {company.status === "REJECTED" && <Button type="button" variant="outline" disabled={saving} onClick={() => void resubmit()}><RotateCcw />Lưu và gửi lại</Button>}
          <Button disabled={saving}>{saving && <Loader2 className="animate-spin" />}{saving ? "Đang lưu..." : "Lưu thay đổi"}</Button>
        </div>
      </form>
    </div>
  );
}

function CompanyField({ name, label, value, required = false }: { name: string; label: string; value: string; required?: boolean }) {
  return <label className="block"><span className="text-sm font-medium text-zinc-700">{label}</span><Input name={name} defaultValue={value} className="mt-1.5" required={required} /></label>;
}
