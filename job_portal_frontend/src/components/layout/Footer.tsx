import Link from "next/link";

import { BrandLogo } from "@/components/layout/BrandLogo";
import { BrandName } from "@/components/layout/BrandName";

export function Footer() {
  return (
    <footer className="border-t border-slate-200 bg-slate-50">
      <div className="mx-auto w-full max-w-[1200px] px-4 py-6 md:px-6 md:py-8">
        <div className="grid gap-6 sm:grid-cols-2 md:grid-cols-[1.5fr_1fr_1fr] md:gap-8">
          <div className="sm:col-span-2 md:col-span-1">
            <div className="flex items-center gap-3">
              <BrandLogo className="size-10" />
              <BrandName />
            </div>
            <p className="mt-2 max-w-sm text-sm leading-6 text-zinc-500">
              Nền tảng tuyển dụng — kết nối ứng viên và nhà tuyển dụng với công nghệ AI
              match giữa CV và tin tuyển dụng.
            </p>
          </div>

          <div>
            <h3 className="text-sm font-semibold text-zinc-800">Dành cho ứng viên</h3>
            <ul className="mt-3 space-y-2 text-sm text-zinc-500">
              <li>
                <Link href="/jobs" className="rounded-sm transition-colors hover:text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary">
                  Tìm việc làm
                </Link>
              </li>
              <li>
                <Link href="/register?role=CANDIDATE" className="rounded-sm transition-colors hover:text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary">
                  Tạo hồ sơ ứng viên
                </Link>
              </li>
            </ul>
          </div>

          <div>
            <h3 className="text-sm font-semibold text-zinc-800">Dành cho nhà tuyển dụng</h3>
            <ul className="mt-3 space-y-2 text-sm text-zinc-500">
              <li>
                <Link href="/employer/jobs" className="rounded-sm transition-colors hover:text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary">
                  Quản lý tin và ứng viên
                </Link>
              </li>
              <li>
                <Link href="/employer/jobs/new" className="rounded-sm transition-colors hover:text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary">
                  Đăng tin tuyển dụng
                </Link>
              </li>
            </ul>
          </div>
        </div>

        <div className="mt-6 border-t border-slate-200 pt-4 text-sm text-zinc-400">
          <p>© {new Date().getFullYear()} Semantic-Job-Platform. Bảo lưu mọi quyền.</p>
        </div>
      </div>
    </footer>
  );
}
