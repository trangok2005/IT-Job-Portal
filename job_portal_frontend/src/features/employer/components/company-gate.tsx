"use client";

import { Building2, RotateCcw } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { getMyCompany } from "@/features/employer/api";
import type { CompanyDto } from "@/features/employer/types";

export function CompanyGate({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const [company, setCompany] = useState<CompanyDto | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const gated = pathname === "/employer/jobs/new";

  const checkCompany = async () => {
    setLoading(true);
    setError(null);
    try {
      setCompany(await getMyCompany());
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Không thể kiểm tra trạng thái công ty.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (!gated) return;
    getMyCompany()
      .then(setCompany)
      .catch((reason: unknown) => {
        setError(reason instanceof Error ? reason.message : "Không thể kiểm tra trạng thái công ty.");
      })
      .finally(() => setLoading(false));
  }, [gated]);

  if (!gated) return children;
  if (loading) return <div className="mx-auto mt-8 h-52 max-w-3xl animate-pulse rounded-xl bg-zinc-100" />;

  if (error) {
    return (
      <div className="mx-auto max-w-2xl px-4 py-16 text-center">
        <p className="rounded-xl bg-red-50 p-4 text-sm text-red-700">{error}</p>
        <Button variant="outline" className="mt-4" onClick={() => void checkCompany()}>
          <RotateCcw /> Thử lại
        </Button>
      </div>
    );
  }

  if (company?.status === "APPROVED") return children;

  return (
    <div className="mx-auto max-w-2xl px-4 py-16 text-center">
      <span className="mx-auto grid size-14 place-items-center rounded-xl bg-amber-50 text-amber-700">
        <Building2 />
      </span>
      <h1 className="mt-4 text-2xl font-bold text-zinc-900">Công ty chưa được duyệt</h1>
      <p className="mt-2 text-sm leading-6 text-zinc-500">
        Bạn chỉ có thể tạo tin mới sau khi hồ sơ công ty được Admin phê duyệt. Trạng thái hiện tại:{" "}
        <strong>{company?.status ?? "Chưa có hồ sơ"}</strong>.
      </p>
      <Button asChild className="mt-6"><Link href="/employer/company">Kiểm tra hồ sơ công ty</Link></Button>
    </div>
  );
}
