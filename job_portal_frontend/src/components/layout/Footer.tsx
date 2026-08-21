import Link from "next/link";

function FacebookIcon(props: React.SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 24 24" fill="currentColor" aria-hidden {...props}>
      <path d="M22 12.06C22 6.5 17.52 2 12 2S2 6.5 2 12.06c0 5.02 3.66 9.18 8.44 9.94v-7.03H7.9v-2.9h2.54V9.85c0-2.5 1.49-3.89 3.77-3.89 1.09 0 2.24.2 2.24.2v2.46h-1.26c-1.24 0-1.63.77-1.63 1.56v1.88h2.78l-.45 2.9h-2.33V22c4.78-.76 8.44-4.92 8.44-9.94Z" />
    </svg>
  );
}

function LinkedinIcon(props: React.SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 24 24" fill="currentColor" aria-hidden {...props}>
      <path d="M20.45 20.45h-3.55v-5.57c0-1.33-.03-3.04-1.85-3.04-1.86 0-2.14 1.45-2.14 2.94v5.67H9.35V9h3.41v1.56h.05c.48-.9 1.64-1.85 3.37-1.85 3.6 0 4.27 2.37 4.27 5.46v6.28ZM5.34 7.43a2.06 2.06 0 1 1 0-4.12 2.06 2.06 0 0 1 0 4.12ZM7.12 20.45H3.56V9h3.56v11.45Z" />
    </svg>
  );
}

function GithubIcon(props: React.SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 24 24" fill="currentColor" aria-hidden {...props}>
      <path d="M12 2a10 10 0 0 0-3.16 19.49c.5.09.68-.22.68-.48v-1.7c-2.78.6-3.37-1.34-3.37-1.34-.45-1.16-1.11-1.47-1.11-1.47-.9-.62.07-.6.07-.6 1 .07 1.53 1.03 1.53 1.03.9 1.52 2.34 1.08 2.91.83.09-.65.35-1.09.63-1.34-2.22-.25-4.56-1.11-4.56-4.94 0-1.09.39-1.98 1.03-2.68-.1-.25-.45-1.27.1-2.64 0 0 .84-.27 2.75 1.02a9.56 9.56 0 0 1 5 0c1.91-1.29 2.75-1.02 2.75-1.02.55 1.37.2 2.39.1 2.64.64.7 1.03 1.59 1.03 2.68 0 3.84-2.34 4.68-4.57 4.93.36.31.68.92.68 1.85V21c0 .27.18.58.69.48A10 10 0 0 0 12 2Z" />
    </svg>
  );
}

export function Footer() {
  return (
    <footer className="border-t border-zinc-100 bg-zinc-50">
      <div className="mx-auto w-full max-w-6xl px-4 py-12 sm:px-6">
        <div className="grid gap-10 md:grid-cols-[1.5fr_1fr_1fr]">
          <div>
            <div className="flex items-center gap-2">
              <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-primary text-lg font-bold text-white">
                J
              </span>
              <span className="text-lg font-bold text-primary">
                IT<span className="text-accent">Job</span> Portal
              </span>
            </div>
            <p className="mt-3 max-w-sm text-sm text-zinc-500">
              Nền tảng tuyển dụng IT — kết nối ứng viên và nhà tuyển dụng với công nghệ AI
              match giữa CV và tin tuyển dụng.
            </p>
            <div className="mt-4 flex items-center gap-3 text-zinc-400">
              <a href="https://facebook.com" target="_blank" rel="noreferrer" aria-label="Facebook">
                <FacebookIcon className="h-5 w-5 hover:text-primary" />
              </a>
              <a href="https://linkedin.com" target="_blank" rel="noreferrer" aria-label="LinkedIn">
                <LinkedinIcon className="h-5 w-5 hover:text-primary" />
              </a>
              <a href="https://github.com" target="_blank" rel="noreferrer" aria-label="GitHub">
                <GithubIcon className="h-5 w-5 hover:text-primary" />
              </a>
            </div>
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
                <Link href="/for-employers" className="hover:text-primary">
                  Dành cho Nhà tuyển dụng
                </Link>
              </li>
              <li>
                <Link href="/register?role=EMPLOYER" className="hover:text-primary">
                  Đăng tin tuyển dụng
                </Link>
              </li>
            </ul>
          </div>
        </div>

        <div className="mt-10 flex flex-col items-center justify-between gap-3 border-t border-zinc-200 pt-6 text-sm text-zinc-400 sm:flex-row">
          <p>© {new Date().getFullYear()} IT Job Portal. Bảo lưu mọi quyền.</p>
          <div className="flex gap-6">
            <span>Điều khoản</span>
            <span>Chính sách bảo mật</span>
            <span>Liên hệ</span>
          </div>
        </div>
      </div>
    </footer>
  );
}
