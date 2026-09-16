import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import { AuthProvider } from "@/lib/auth-provider";
import { JDImportProvider } from "@/features/employer/jd-import-provider";
import { CandidateResumeImportProvider } from "@/features/candidates/candidate-resume-import-provider";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "IT Job Portal",
  description: "Nền tảng tuyển dụng IT với điểm phù hợp giữa CV và JD.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html
      lang="vi"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
    >
      <body className="min-h-full flex flex-col">
        <AuthProvider>
          <JDImportProvider>
            <CandidateResumeImportProvider>
              {children}
            </CandidateResumeImportProvider>
          </JDImportProvider>
        </AuthProvider>
      </body>
    </html>
  );
}
