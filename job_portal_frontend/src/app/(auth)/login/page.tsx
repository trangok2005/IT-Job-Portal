import { BrainCircuit, CheckCircle2, Search, TrendingUp } from "lucide-react";

import { LoginForm } from "@/features/auth/components/login-form";

export const metadata = { title: "Đăng nhập | IT Job Portal" };

const BENEFITS = [
  "AI match việc làm phù hợp với kỹ năng của bạn",
  "Cập nhật tin tuyển dụng IT mới nhất mỗi ngày",
  "Hồ sơ ứng tuyển được gợi ý tới nhà tuyển dụng phù hợp",
];

export default async function LoginPage({ searchParams }: PageProps<"/login">) {
  const { redirect_to: redirectTo } = await searchParams;
  const destination = Array.isArray(redirectTo) ? redirectTo[0] : redirectTo;

  return (
    <div className="grid w-full max-w-5xl overflow-hidden rounded-2xl border border-zinc-200 bg-white shadow-lg shadow-zinc-900/5 md:grid-cols-2">
      {/* Left: illustration */}
      <div className="relative hidden flex-col justify-between overflow-hidden bg-gradient-to-br from-primary-800 via-primary-600 to-primary-500 p-10 text-white md:flex">
        <div className="absolute -right-16 -top-16 h-56 w-56 rounded-full bg-white/10" />
        <div className="absolute -bottom-20 -left-10 h-64 w-64 rounded-full bg-accent/20" />

        <div className="relative">
          <span className="inline-flex items-center gap-2 rounded-full bg-white/10 px-3.5 py-1.5 text-xs font-medium backdrop-blur">
            <BrainCircuit className="h-4 w-4" />
            AI Job Matching
          </span>
          <h2 className="mt-5 text-2xl font-bold leading-snug">
            Tìm công việc IT phù hợp với năng lực của bạn
          </h2>

          <ul className="mt-8 space-y-4 text-sm">
            {BENEFITS.map((benefit) => (
              <li key={benefit} className="flex items-start gap-3">
                <CheckCircle2 className="mt-0.5 h-5 w-5 shrink-0 text-accent" />
                <span className="leading-relaxed text-primary-50">{benefit}</span>
              </li>
            ))}
          </ul>
        </div>

        {/* Mock job card */}
        <div className="relative rounded-2xl border border-white/15 bg-white/10 p-5 backdrop-blur">
          <div className="flex items-center gap-3">
            <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-white/15 font-bold">
              T
            </span>
            <div>
              <p className="text-sm font-semibold">Backend Developer (Python/Django)</p>
              <p className="text-xs text-primary-100">TechCorp Vietnam · Hà Nội</p>
            </div>
          </div>
          <div className="mt-4 flex items-center justify-between text-xs">
            <span className="inline-flex items-center gap-1 text-accent">
              <TrendingUp className="h-3.5 w-3.5" /> 15 - 25 triệu
            </span>
            <span className="inline-flex items-center gap-1 text-primary-100">
              <Search className="h-3.5 w-3.5" /> Match 92%
            </span>
          </div>
        </div>
      </div>

      {/* Right: card */}
      <div className="flex flex-col justify-center p-8 sm:p-12">
        <h1 className="text-2xl font-bold text-zinc-900">Đăng nhập</h1>
        <p className="mt-1 text-sm text-zinc-500">
          Đăng nhập để tiếp tục đến với IT Job Portal.
        </p>
        <div className="mt-8">
          <LoginForm redirectTo={destination} />
        </div>
      </div>
    </div>
  );
}
