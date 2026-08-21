"use client";

import { Button } from "@/components/ui/button";

export default function JobsError({ reset }: { reset: () => void }) {
  return (
    <div className="mx-auto max-w-xl px-4 py-20 text-center">
      <h1 className="text-xl font-bold text-zinc-900">Không thể tải kết quả tìm kiếm</h1>
      <p className="mt-2 text-sm text-zinc-500">Hệ thống đang gặp sự cố tạm thời. Vui lòng thử lại.</p>
      <Button className="mt-5" onClick={reset}>Thử lại</Button>
    </div>
  );
}
