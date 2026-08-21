import { ArrowRight, BrainCircuit, ShieldCheck, Users } from "lucide-react";
import Link from "next/link";

import { Button } from "@/components/ui/button";

const FEATURES = [
  {
    icon: Users,
    title: "Tiếp cận ứng viên IT chất lượng",
    description: "Nguồn hồ sơ ứng viên công nghệ có kỹ năng được xác thực.",
  },
  {
    icon: BrainCircuit,
    title: "AI match thông minh",
    description: "Tự động gợi ý ứng viên phù hợp nhất với JD của bạn.",
  },
  {
    icon: ShieldCheck,
    title: "Quản lý tuyển dụng minh bạch",
    description: "Theo dõi trạng thái ứng tuyển, duyệt hồ sơ tập trung.",
  },
];

export const metadata = { title: "Dành cho Nhà tuyển dụng | IT Job Portal" };

export default function EmployerPage() {
  return (
    <div>
      <section className="bg-gradient-to-b from-primary-50 to-white">
        <div className="mx-auto flex w-full max-w-6xl flex-col items-center px-4 py-16 text-center sm:px-6">
          <h1 className="text-3xl font-extrabold tracking-tight text-zinc-900 sm:text-5xl">
            Tuyển dụng IT <span className="text-accent">dễ dàng hơn</span>
          </h1>
          <p className="mt-4 max-w-2xl text-sm text-zinc-500 sm:text-base">
            Đăng tin tuyển dụng, tiếp cận ứng viên phù hợp và quản lý quy trình tuyển dụng trên
            một nền tảng duy nhất.
          </p>
          <div className="mt-8 flex flex-col gap-3 sm:flex-row">
            <Button asChild size="lg" variant="accent">
              <Link href="/register?role=EMPLOYER">
                Đăng tin tuyển dụng ngay <ArrowRight className="h-4 w-4" />
              </Link>
            </Button>
            <Button asChild size="lg" variant="outline">
              <Link href="/jobs">Xem việc làm đang tuyển</Link>
            </Button>
          </div>
        </div>
      </section>

      <section className="mx-auto w-full max-w-6xl px-4 pb-16 sm:px-6">
        <div className="grid gap-6 sm:grid-cols-3">
          {FEATURES.map((feature) => (
            <div
              key={feature.title}
              className="rounded-xl border border-zinc-200 bg-white p-6 shadow-sm"
            >
              <span className="flex h-11 w-11 items-center justify-center rounded-xl bg-primary-50 text-primary-700">
                <feature.icon className="h-5 w-5" />
              </span>
              <h3 className="mt-4 font-semibold text-zinc-900">{feature.title}</h3>
              <p className="mt-2 text-sm text-zinc-500">{feature.description}</p>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
