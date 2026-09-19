"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { AlertCircle, Building2, CircleCheck, FileText, Loader2, LogOut, Menu, ShieldCheck, Sparkles, UserRound, X } from "lucide-react";
import { useState } from "react";

import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import { BrandLogo } from "@/components/layout/BrandLogo";
import { BrandName } from "@/components/layout/BrandName";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { useAuth } from "@/lib/auth-provider";
import { useJDImport } from "@/features/employer/jd-import-provider";
import { useCandidateResumeImport } from "@/features/candidates/candidate-resume-import-provider";
import { ROLE_HOME } from "@/lib/auth";
import type { UserRole } from "@/lib/types";
import { cn } from "@/lib/utils";

const PUBLIC_NAV_LINKS = [
  { href: "/", label: "Trang chủ" },
  { href: "/jobs", label: "Tìm việc" },
];

const ROLE_NAV_LINKS: Record<UserRole, Array<{ href: string; label: string }>> = {
  CANDIDATE: [
    { href: "/jobs", label: "Tìm việc" },
    { href: "/candidate/profile", label: "Hồ sơ" },
    { href: "/candidate/applications", label: "Đơn ứng tuyển" },
  ],
  EMPLOYER: [
    { href: "/employer", label: "Tổng quan" },
    { href: "/employer/company", label: "Công ty" },
    { href: "/employer/jobs", label: "Tin tuyển dụng" },
  ],
  ADMIN: [
    { href: "/admin", label: "Tổng quan" },
    { href: "/admin/companies", label: "Công ty" },
    { href: "/admin/users", label: "Người dùng" },
    { href: "/admin/skills", label: "Skill & trọng số" },
  ],
};

function userInitials(firstName: string, lastName: string, email: string) {
  const parts = [firstName, lastName].filter(Boolean);
  if (parts.length) return parts.map((p) => p[0]).join("").slice(0, 2).toUpperCase();
  return email.slice(0, 2).toUpperCase();
}

function isActiveLink(pathname: string, href: string) {
  if (href === "/employer" || href === "/admin") return pathname === href;
  return pathname === href || pathname.startsWith(`${href}/`);
}

type ImportStatusLinkProps = {
  status: string;
  href: string;
  processingText: string;
  successText: string;
  failedText: string;
  mobile?: boolean;
  onClick?: () => void;
};

function ImportStatusLink({
  status,
  href,
  processingText,
  successText,
  failedText,
  mobile = false,
  onClick,
}: ImportStatusLinkProps) {
  let text = processingText;
  if (status === "SUCCESS") text = successText;
  if (status === "FAILED") text = failedText;

  return (
    <Link
      href={href}
      onClick={onClick}
      className={mobile
        ? "flex items-center gap-2 rounded-lg bg-primary-50 px-3 py-2.5 text-sm font-medium text-primary"
        : "flex items-center gap-2 rounded-full border border-zinc-200 px-3 py-2 text-xs font-medium text-zinc-700 hover:border-primary-200 hover:text-primary"
      }
    >
      {["PENDING", "PROCESSING"].includes(status) && <Loader2 className="size-4 animate-spin" />}
      {status === "SUCCESS" && <CircleCheck className={cn("size-4", !mobile && "text-emerald-600")} />}
      {status === "FAILED" && <AlertCircle className="size-4 text-red-600" />}
      {text}
    </Link>
  );
}

export function Navbar() {
  const { user, signOut } = useAuth();
  const { jdImport } = useJDImport();
  const { resumeImport } = useCandidateResumeImport();
  const pathname = usePathname();
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const navLinks = user ? ROLE_NAV_LINKS[user.role] : PUBLIC_NAV_LINKS;
  const homeHref = user ? ROLE_HOME[user.role] : "/";
  let importLink: ImportStatusLinkProps | null = null;
  if (user?.role === "EMPLOYER" && jdImport) {
    importLink = {
      status: jdImport.status,
      href: jdImport.status === "SUCCESS"
        ? `/employer/jobs/new?import_id=${jdImport.id}`
        : "/employer/jobs/new",
      processingText: "Đang đọc JD",
      successText: "JD đã sẵn sàng",
      failedText: "JD lỗi",
    };
  }
  if (user?.role === "CANDIDATE" && resumeImport) {
    importLink = {
      status: resumeImport.parse_status,
      href: resumeImport.parse_status === "SUCCESS"
        ? `/candidate/profile?resume_import_id=${resumeImport.id}`
        : "/candidate/profile",
      processingText: "Đang phân tích CV",
      successText: "CV đã phân tích xong",
      failedText: "CV lỗi",
    };
  }

  const handleSignOut = () => {
    signOut();
    router.push("/");
  };

  const dropdownItems = user ? (
    <>
      <DropdownMenuItem asChild>
        <Link href={user.role === "CANDIDATE" ? "/candidate/profile" : ROLE_HOME[user.role]}>
          {user.role === "CANDIDATE" && <UserRound className="mr-2" />}
          {user.role === "EMPLOYER" && <Building2 className="mr-2" />}
          {user.role === "ADMIN" && <ShieldCheck className="mr-2" />}
          {user.role === "CANDIDATE" ? "Hồ sơ" : user.role === "EMPLOYER" ? "Không gian nhà tuyển dụng" : "Quản trị hệ thống"}
        </Link>
      </DropdownMenuItem>
      {user.role === "CANDIDATE" && (
        <>
          <DropdownMenuItem asChild>
            <Link href="/jobs?tab=recommended">
              <Sparkles className="mr-2" /> Việc làm phù hợp
            </Link>
          </DropdownMenuItem>
          <DropdownMenuItem asChild>
            <Link href="/candidate/applications">
              <FileText className="mr-2" /> Đơn ứng tuyển
            </Link>
          </DropdownMenuItem>
        </>
      )}
      <DropdownMenuSeparator />
      <DropdownMenuItem onSelect={handleSignOut}>
        <LogOut className="mr-2" /> Đăng xuất
      </DropdownMenuItem>
    </>
  ) : null;

  return (
    <header className="sticky top-0 z-40 border-b border-zinc-100 bg-white/90 backdrop-blur">
      <div className="mx-auto flex h-20 w-full max-w-6xl items-center justify-between px-4 sm:px-6">
        <Link href={homeHref} className="flex items-center gap-2">
          <BrandLogo />
          <BrandName />
        </Link>

        <nav className="hidden items-center gap-6 md:flex">
          {navLinks.map((link) => (
            <Link
              key={link.href}
              href={link.href}
              className={cn(
                "text-sm font-medium transition-colors hover:text-primary",
                isActiveLink(pathname, link.href) ? "text-primary" : "text-zinc-600",
              )}
            >
              {link.label}
            </Link>
          ))}
        </nav>

        <div className="hidden items-center gap-3 md:flex">
          {importLink && <ImportStatusLink {...importLink} />}
          {!user && (
            <>
              <Button asChild variant="ghost">
                <Link href="/login">Đăng nhập</Link>
              </Button>
              <Button asChild>
                <Link href="/register">Đăng ký</Link>
              </Button>
            </>
          )}
          {user && (
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <button
                  type="button"
                  className="flex items-center gap-2 rounded-outline-none focus-visible:ring-2 focus-visible:ring-primary"
                  aria-label="Menu tài khoản"
                >
                  {user.role === "CANDIDATE" && <span className="text-sm font-medium text-zinc-600">Tài khoản</span>}
                  <Avatar className="h-9 w-9">
                    <AvatarFallback>
                      {userInitials(user.first_name, user.last_name, user.email)}
                    </AvatarFallback>
                  </Avatar>
                </button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="w-56">
                <DropdownMenuLabel>
                  <p className="truncate text-sm font-semibold text-zinc-800">
                    {[user.first_name, user.last_name].filter(Boolean).join(" ") || user.email}
                  </p>
                  <p className="truncate text-xs font-normal text-zinc-500">{user.email}</p>
                </DropdownMenuLabel>
                <DropdownMenuSeparator />
                {dropdownItems}
              </DropdownMenuContent>
            </DropdownMenu>
          )}
        </div>

        <button
          type="button"
          className="flex h-10 w-10 items-center justify-center rounded-xl text-zinc-700 hover:bg-zinc-100 md:hidden"
          onClick={() => setOpen((v) => !v)}
          aria-label="Mở menu"
        >
          {open ? <X className="size-5" /> : <Menu className="size-5" />}
        </button>
      </div>

      {open && (
        <div className="border-t border-zinc-100 bg-white px-4 py-4 md:hidden">
          <nav className="flex flex-col gap-1">
            {navLinks.map((link) => (
              <Link
                key={link.href}
                href={link.href}
                onClick={() => setOpen(false)}
                className={cn(
                  "rounded-lg px-3 py-2.5 text-sm font-medium",
                  isActiveLink(pathname, link.href)
                    ? "bg-primary-50 text-primary"
                    : "text-zinc-700 hover:bg-zinc-50",
                )}
              >
                {link.label}
              </Link>
            ))}
            {importLink && (
              <ImportStatusLink {...importLink} mobile onClick={() => setOpen(false)} />
            )}
            {!user && (
              <div className="mt-3 flex flex-col gap-2 border-t border-zinc-100 pt-3">
                <Button asChild variant="outline" onClick={() => setOpen(false)}>
                  <Link href="/login">Đăng nhập</Link>
                </Button>
                <Button asChild onClick={() => setOpen(false)}>
                  <Link href="/register">Đăng ký</Link>
                </Button>
              </div>
            )}
            {user && (
              <div className="mt-3 flex flex-col gap-1 border-t border-zinc-100 pt-3">
                <button
                  type="button"
                  onClick={() => {
                    setOpen(false);
                    handleSignOut();
                  }}
                  className="rounded-lg px-3 py-2.5 text-left text-sm font-medium text-zinc-700 hover:bg-zinc-50"
                >
                  Đăng xuất
                </button>
              </div>
            )}
          </nav>
        </div>
      )}
    </header>
  );
}
