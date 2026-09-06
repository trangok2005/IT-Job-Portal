import Link from "next/link";
import { BrandLogo } from "@/components/layout/BrandLogo";
import { BrandName } from "@/components/layout/BrandName";
import { GuestOnly } from "@/features/auth/components/guest-only";

export default function AuthLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-screen flex-col bg-zinc-50">
      <header className="flex h-20 items-center justify-between border-b border-zinc-100 bg-white px-4 sm:px-6">
        <Link href="/" className="flex items-center gap-2">
          <BrandLogo />
          <BrandName />
        </Link>
        <Link
          href="/"
          className="text-sm font-medium text-zinc-500 transition-colors hover:text-primary"
        >
          Về trang chủ
        </Link>
      </header>
      <main className="flex flex-1 items-center justify-center px-4 py-10"><GuestOnly>{children}</GuestOnly></main>
    </div>
  );
}
