"use client";

import { Search, ShieldCheck, UserRound } from "lucide-react";
import { useEffect, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { getAdminUsers, setUserLocked } from "@/features/admin/api";
import type { AdminUserQuery, UserDto } from "@/features/admin/types";

export function UsersAdmin() {
  const [items, setItems] = useState<UserDto[]>([]);
  const [search, setSearch] = useState("");
  const [role, setRole] = useState<AdminUserQuery["role"] | "">("");
  const [active, setActive] = useState<"" | "true" | "false">("");
  const [loading, setLoading] = useState(true);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await getAdminUsers({
        search: search || undefined,
        role: role || undefined,
        is_active: active === "" ? undefined : active === "true",
      });
      setItems(response.results);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Không thể tải người dùng.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    getAdminUsers()
      .then((response) => setItems(response.results))
      .catch((reason: unknown) => {
        setError(reason instanceof Error ? reason.message : "Không thể tải người dùng.");
      })
      .finally(() => setLoading(false));
  }, []);

  const toggleLock = async (user: UserDto) => {
    const action = user.is_active ? "khóa" : "mở khóa";
    if (!window.confirm(`Xác nhận ${action} tài khoản ${user.email}?`)) return;
    setBusyId(user.id);
    setError(null);
    try {
      await setUserLocked(user.id, user.is_active);
      await load();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : `Không thể ${action} tài khoản.`);
    } finally {
      setBusyId(null);
    }
  };

  return (
    <div className="mx-auto max-w-6xl px-4 py-7 sm:px-6 lg:px-8">
      <div className="flex items-start gap-3">
        <span className="grid size-11 place-items-center rounded-xl bg-primary text-white">
          <UserRound className="size-5" />
        </span>
        <div>
          <h1 className="text-2xl font-bold text-zinc-900">Tài khoản người dùng</h1>
          <p className="mt-1 text-sm text-zinc-500">Tra cứu và kiểm soát quyền truy cập hệ thống.</p>
        </div>
      </div>

      <form
        onSubmit={(event) => {
          event.preventDefault();
          void load();
        }}
        className="mt-6 grid gap-2 rounded-xl border border-zinc-200 bg-white p-4 shadow-sm md:grid-cols-[1fr_170px_170px_auto]"
      >
        <div className="relative">
          <Search className="absolute left-3.5 top-1/2 size-4 -translate-y-1/2 text-zinc-400" />
          <Input
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            className="pl-10"
            placeholder="Email, username, họ tên..."
          />
        </div>
        <select
          value={role}
          onChange={(event) => setRole(event.target.value as typeof role)}
          className="h-11 rounded-xl border border-zinc-300 bg-white px-3 text-sm"
        >
          <option value="">Mọi vai trò</option>
          <option value="CANDIDATE">Candidate</option>
          <option value="EMPLOYER">Employer</option>
          <option value="ADMIN">Admin</option>
        </select>
        <select
          value={active}
          onChange={(event) => setActive(event.target.value as typeof active)}
          className="h-11 rounded-xl border border-zinc-300 bg-white px-3 text-sm"
        >
          <option value="">Mọi trạng thái</option>
          <option value="true">Đang hoạt động</option>
          <option value="false">Đã khóa</option>
        </select>
        <Button disabled={loading}>{loading ? "Đang tải..." : "Tìm kiếm"}</Button>
      </form>

      {error && <p className="mt-4 rounded-xl bg-red-50 p-4 text-sm text-red-700">{error}</p>}

      <div className="mt-5 overflow-hidden rounded-xl border border-zinc-200 bg-white shadow-sm">
        {!loading && items.length === 0 && (
          <p className="p-10 text-center text-sm text-zinc-500">Không tìm thấy tài khoản phù hợp.</p>
        )}
        {items.map((user) => (
          <div
            key={user.id}
            className="flex flex-col gap-3 border-b border-zinc-100 p-4 last:border-0 sm:flex-row sm:items-center"
          >
            <span className="grid size-10 shrink-0 place-items-center rounded-full bg-primary-50 font-bold text-primary">
              {user.email.charAt(0).toUpperCase()}
            </span>
            <div className="min-w-0 flex-1">
              <p className="truncate text-sm font-semibold text-zinc-900">{user.email}</p>
              <p className="mt-1 text-xs text-zinc-500">
                {[user.first_name, user.last_name].filter(Boolean).join(" ") || user.username}
                <span className="mx-2 text-zinc-300">/</span>
                {user.auth_provider}
              </p>
            </div>
            <div className="flex flex-wrap items-center gap-2">
              <Badge>{user.role}</Badge>
              <Badge variant={user.is_active ? "success" : "outline"}>
                {user.is_active ? "Hoạt động" : "Đã khóa"}
              </Badge>
              {user.role === "ADMIN" ? (
                <span title="Không thể khóa tài khoản Admin">
                  <ShieldCheck className="size-5 text-zinc-400" />
                </span>
              ) : (
                <Button
                  size="sm"
                  variant="outline"
                  disabled={busyId === user.id}
                  onClick={() => void toggleLock(user)}
                >
                  {busyId === user.id ? "Đang lưu..." : user.is_active ? "Khóa" : "Mở khóa"}
                </Button>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
