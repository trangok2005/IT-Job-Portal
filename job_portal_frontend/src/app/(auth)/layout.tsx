import Link from "next/link";

export default function AuthLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-screen flex-col bg-zinc-50">
      <header className="flex h-16 items-center justify-between border-b border-zinc-100 bg-white px-4 sm:px-6">
        <Link href="/" className="flex items-center gap-2">
          <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-primary text-lg font-bold text-white">
            J
          </span>
          <span className="text-lg font-bold text-primary">
            IT<span className="text-accent">Job</span> Portal
          </span>
        </Link>
        <Link
          href="/"
          className="text-sm font-medium text-zinc-500 transition-colors hover:text-primary"
        >
          Về trang chủ
        </Link>
      </header>
      <main className="flex flex-1 items-center justify-center px-4 py-10">{children}</main>
    </div>
  );
}
