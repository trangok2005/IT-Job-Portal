"use client";

import { BriefcaseBusiness, Pencil, Plus, Trash2 } from "lucide-react";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import type { ExperienceDto, ExperiencePayload } from "@/features/candidates/types";
import {
  EmptySection,
  FieldLabel,
  ProfileSection,
  textareaClassName,
} from "@/features/candidates/components/profile-section";

function formatDate(value: string | null | undefined) {
  if (!value) return "Hiện tại";
  return new Intl.DateTimeFormat("vi-VN", { month: "2-digit", year: "numeric" }).format(
    new Date(`${value}T00:00:00`),
  );
}

export function ExperienceSection({
  items,
  pending,
  onChange,
}: {
  items: ExperienceDto[];
  pending: boolean;
  onChange: (items: ExperienceDto[]) => void;
}) {
  const [formOpen, setFormOpen] = useState(false);
  const [editing, setEditing] = useState<ExperienceDto | null>(null);
  const [isCurrent, setIsCurrent] = useState(false);

  const openForm = (item?: ExperienceDto) => {
    setEditing(item ?? null);
    setIsCurrent(item?.is_current ?? false);
    setFormOpen(true);
  };

  const closeForm = () => {
    setFormOpen(false);
    setEditing(null);
    setIsCurrent(false);
  };

  const submit = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const payload: ExperiencePayload = {
      company_name: String(form.get("company_name") ?? "").trim(),
      position: String(form.get("position") ?? "").trim(),
      start_date: String(form.get("start_date") ?? "") || null,
      end_date: isCurrent ? null : String(form.get("end_date") ?? "") || null,
      is_current: isCurrent,
      description: String(form.get("description") ?? "").trim(),
    };
    const now = new Date().toISOString();
    const item: ExperienceDto = {
      id: editing?.id ?? crypto.randomUUID(),
      ...payload,
      created_at: editing?.created_at ?? now,
      updated_at: now,
    };
    onChange(editing ? items.map((current) => current.id === editing.id ? item : current) : [...items, item]);
    closeForm();
  };

  const remove = (item: ExperienceDto) => {
    if (!window.confirm(`Xóa kinh nghiệm tại ${item.company_name}?`)) return;
    onChange(items.filter((current) => current.id !== item.id));
  };

  return (
    <ProfileSection
      id="experience"
      icon={BriefcaseBusiness}
      title="Kinh nghiệm làm việc"
      description="Những vai trò và dự án thể hiện năng lực của bạn."
      action={
        !formOpen ? (
          <Button type="button" variant="outline" size="sm" onClick={() => openForm()}>
            <Plus />
            <span className="hidden sm:inline">Thêm</span>
          </Button>
        ) : undefined
      }
    >
      {formOpen && (
        <form onSubmit={submit} className="mb-6 space-y-4 rounded-xl border border-primary-100 bg-primary-50/40 p-4">
          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <FieldLabel htmlFor="experience-company">Công ty *</FieldLabel>
              <Input
                id="experience-company"
                name="company_name"
                defaultValue={editing?.company_name}
                required
              />
            </div>
            <div>
              <FieldLabel htmlFor="experience-position">Vị trí *</FieldLabel>
              <Input
                id="experience-position"
                name="position"
                defaultValue={editing?.position}
                required
              />
            </div>
            <div>
              <FieldLabel htmlFor="experience-start">Bắt đầu</FieldLabel>
              <Input
                id="experience-start"
                name="start_date"
                type="date"
                defaultValue={editing?.start_date ?? ""}
              />
            </div>
            <div>
              <FieldLabel htmlFor="experience-end">Kết thúc</FieldLabel>
              <Input
                id="experience-end"
                name="end_date"
                type="date"
                defaultValue={editing?.end_date ?? ""}
                disabled={isCurrent}
              />
            </div>
          </div>
          <label className="flex cursor-pointer items-center gap-2 text-sm text-zinc-700">
            <input
              type="checkbox"
              checked={isCurrent}
              onChange={(event) => setIsCurrent(event.target.checked)}
              className="size-4 accent-primary"
            />
            Tôi đang làm việc tại đây
          </label>
          <div>
            <FieldLabel htmlFor="experience-description">Mô tả công việc</FieldLabel>
            <textarea
              id="experience-description"
              name="description"
              defaultValue={editing?.description}
              className={textareaClassName}
              placeholder="Trách nhiệm, công nghệ sử dụng và kết quả nổi bật..."
            />
          </div>
          <div className="flex justify-end gap-2">
            <Button type="button" variant="ghost" onClick={closeForm} disabled={pending}>Hủy</Button>
            <Button type="submit" disabled={pending}>{pending ? "Đang lưu..." : "Lưu kinh nghiệm"}</Button>
          </div>
        </form>
      )}

      {!items.length ? (
        <EmptySection>Bạn chưa thêm kinh nghiệm. Fresher có thể bổ sung dự án hoặc kỳ thực tập.</EmptySection>
      ) : (
        <div className="divide-y divide-zinc-100">
          {items.map((item) => (
            <div key={item.id} className="py-5 first:pt-0 last:pb-0">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <h3 className="font-semibold text-zinc-900">{item.position}</h3>
                  <p className="mt-1 text-sm font-medium text-primary">{item.company_name}</p>
                  <p className="mt-1 text-xs font-medium text-zinc-400">
                    {formatDate(item.start_date)} – {item.is_current ? "Hiện tại" : formatDate(item.end_date)}
                  </p>
                </div>
                <div className="flex shrink-0">
                  <Button type="button" variant="ghost" size="icon" aria-label="Sửa kinh nghiệm" onClick={() => openForm(item)}>
                    <Pencil />
                  </Button>
                  <Button
                    type="button"
                    variant="ghost"
                    size="icon"
                    className="text-red-500 hover:bg-red-50 hover:text-red-600"
                    aria-label="Xóa kinh nghiệm"
                    onClick={() => remove(item)}
                  >
                    <Trash2 />
                  </Button>
                </div>
              </div>
              {item.description && <p className="mt-3 whitespace-pre-line text-sm leading-6 text-zinc-600">{item.description}</p>}
            </div>
          ))}
        </div>
      )}
    </ProfileSection>
  );
}
