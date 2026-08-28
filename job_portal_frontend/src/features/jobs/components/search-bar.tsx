"use client";

import { useRouter } from "next/navigation";
import { Search } from "lucide-react";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

// Đồng bộ với JobListQuerySerializer (backend): chữ/số tiếng Việt,
// khoảng trắng và ký tự kỹ thuật dùng trong tên skill.
const KEYWORD_ALLOWED_RE = /^[\p{L}\p{N}\s+#./\-&'()]+$/u;
// Chuỗi vô nghĩa kiểu "+++", "---" bị loại: cần ít nhất một chữ/số.
const KEYWORD_HAS_ALNUM_RE = /\p{L}|\p{N}/u;
const KEYWORD_MAX_LENGTH = 100;

export function validateKeyword(value: string): string | null {
  const normalized = value.replace(/\s+/g, " ").trim();
  if (!normalized) return null;
  if (normalized.length > KEYWORD_MAX_LENGTH) {
    return `Từ khóa tìm kiếm tối đa ${KEYWORD_MAX_LENGTH} ký tự.`;
  }
  if (!KEYWORD_ALLOWED_RE.test(normalized)) {
    return "Từ khóa chỉ được chứa chữ, số, khoảng trắng và ký tự như + # . - / & ' ( ).";
  }
  if (!KEYWORD_HAS_ALNUM_RE.test(normalized)) {
    return "Từ khóa tìm kiếm phải chứa ít nhất một chữ cái hoặc chữ số.";
  }
  return null;
}

export function SearchBar({
  initialKeyword = "",
}: {
  initialKeyword?: string;
}) {
  const router = useRouter();
  const [keyword, setKeyword] = useState(initialKeyword);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const validationError = validateKeyword(keyword);
    if (validationError) {
      setError(validationError);
      return;
    }
    setError(null);
    const params = new URLSearchParams(window.location.search);
    if (keyword.trim()) params.set("keyword", keyword.trim());
    else params.delete("keyword");
    params.delete("page");
    router.push(`/jobs${params.toString() ? `?${params.toString()}` : ""}`);
  };

  return (
    <form
      onSubmit={handleSubmit}
      className="flex w-full flex-col gap-2 rounded-2xl border border-zinc-200 bg-white p-2 shadow-lg shadow-primary-900/5 sm:flex-row sm:items-center"
    >
      <div className="flex-1">
        <div className="relative">
          <Search className="pointer-events-none absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-zinc-400" />
          <Input
            value={keyword}
            onChange={(e) => setKeyword(e.target.value)}
            placeholder="Vị trí / công ty / kỹ năng"
            aria-invalid={Boolean(error)}
            className="h-12 border-0 bg-transparent pl-10 shadow-none focus-visible:ring-0"
          />
        </div>
        {error && <p className="mt-1 pl-10 text-xs text-red-600">{error}</p>}
      </div>
      <Button type="submit" size="lg" className="h-12 shrink-0 sm:w-32">
        Tìm kiếm
      </Button>
    </form>
  );
}
