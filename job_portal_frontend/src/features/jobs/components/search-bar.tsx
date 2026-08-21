"use client";

import { useRouter } from "next/navigation";
import { MapPin, Search } from "lucide-react";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

const LOCATIONS = ["", "Hà Nội", "Hồ Chí Minh", "Đà Nẵng", "Hải Phòng", "Cần Thơ"];

export function SearchBar({
  initialKeyword = "",
  initialLocation = "",
}: {
  initialKeyword?: string;
  initialLocation?: string;
}) {
  const router = useRouter();
  const [keyword, setKeyword] = useState(initialKeyword);
  const [location, setLocation] = useState(initialLocation);

  const handleSubmit = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const params = new URLSearchParams(window.location.search);
    if (keyword.trim()) params.set("keyword", keyword.trim());
    else params.delete("keyword");
    if (location) params.set("location", location);
    else params.delete("location");
    params.delete("page");
    router.push(`/jobs${params.toString() ? `?${params.toString()}` : ""}`);
  };

  return (
    <form
      onSubmit={handleSubmit}
      className="flex w-full flex-col gap-2 rounded-2xl border border-zinc-200 bg-white p-2 shadow-lg shadow-primary-900/5 sm:flex-row sm:items-center"
    >
      <div className="relative flex-1">
        <Search className="pointer-events-none absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-zinc-400" />
        <Input
          value={keyword}
          onChange={(e) => setKeyword(e.target.value)}
          placeholder="Vị trí / công ty / kỹ năng"
          className="h-12 border-0 bg-transparent pl-10 shadow-none focus-visible:ring-0"
        />
      </div>
      <div className="hidden h-8 w-px bg-zinc-200 sm:block" />
      <div className="relative sm:w-48">
        <MapPin className="pointer-events-none absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-zinc-400" />
        <select
          value={location}
          onChange={(e) => setLocation(e.target.value)}
          className="h-12 w-full appearance-none rounded-xl border-0 bg-transparent pl-10 pr-8 text-sm text-zinc-700 outline-none focus-visible:ring-0"
        >
          <option value="">Tất cả địa điểm</option>
          {LOCATIONS.filter(Boolean).map((loc) => (
            <option key={loc} value={loc}>
              {loc}
            </option>
          ))}
        </select>
      </div>
      <Button type="submit" size="lg" className="h-12 shrink-0 sm:w-32">
        Tìm kiếm
      </Button>
    </form>
  );
}
