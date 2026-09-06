import Link from "next/link";

import { BrandLogo } from "@/components/layout/BrandLogo";
import { BrandName } from "@/components/layout/BrandName";

export function Footer() {
  return (
    <footer className="border-t border-zinc-100 bg-zinc-50">
      <div className="mx-auto w-full max-w-6xl px-4 py-12 sm:px-6">
        <div className="grid gap-10 md:grid-cols-[1.5fr_1fr_1fr]">
          <div>
            <div className="flex items-center gap-4">
              <BrandLogo className="size-24" />
              <BrandName />
            </div>
            <p className="mt-3 max-w-sm text-sm text-zinc-500">
              Nền tảng tuyển dụng IT — kết nối ứng viên và nhà tuyển dụng với công nghệ AI
              match giữa CV và tin tuyển dụng.
            </p>
          </div>

          <div>
            <h3 className="text-sm font-semibold text-zinc-800">Dành cho ứng viên</h3>
            <ul className="mt-4 space-y-3 text-sm text-zinc-500">
              <li>
                <Link href="/jobs" className="hover:text-primary">
                  Tìm việc làm
                </Link>
              </li>
              <li>
                <Link href="/register?role=CANDIDATE" className="hover:text-primary">
                  Tạo hồ sơ ứng viên
                </Link>
              </li>
            </ul>
          </div>

          <div>
            <h3 className="text-sm font-semibold text-zinc-800">Dành cho nhà tuyển dụng</h3>
            <ul className="mt-4 space-y-3 text-sm text-zinc-500">
              <li>
                <Link href="/employer/jobs" className="hover:text-primary">
                  Quản lý tin và ứng viên
                </Link>
              </li>
              <li>
                <Link href="/employer/jobs/new" className="hover:text-primary">
                  Đăng tin tuyển dụng
                </Link>
              </li>
            </ul>
          </div>
        </div>

        <div className="mt-10 flex flex-col items-center justify-between gap-3 border-t border-zinc-200 pt-6 text-sm text-zinc-400 sm:flex-row">
          <p>© {new Date().getFullYear()} IT Job Portal. Bảo lưu mọi quyền.</p>
        </div>
      </div>
    </footer>
  );
}
