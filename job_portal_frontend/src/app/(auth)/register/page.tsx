import { RegisterForm } from "@/features/auth/components/register-form";

export const metadata = { title: "Đăng ký | IT Job Portal" };

export default async function RegisterPage({ searchParams }: { searchParams: Promise<{ role?: string }> }) {
  const { role } = await searchParams;
  return <RegisterForm initialRole={role === "EMPLOYER" ? "EMPLOYER" : "CANDIDATE"} />;
}
