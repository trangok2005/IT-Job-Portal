"use client";

import { GraduationCap, Pencil, Plus, Trash2 } from "lucide-react";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import type { DegreeLevel, EducationDto, EducationPayload } from "@/features/candidates/types";
import {
  EmptySection,
  FieldLabel,
  ProfileSection,
  textareaClassName,
} from "@/features/candidates/components/profile-section";

function formatDate(value: string | null | undefined, fallback = "Hiện tại") {
  if (!value) return fallback;
  return new Intl.DateTimeFormat("vi-VN", { month: "2-digit", year: "numeric" }).format(
    new Date(`${value}T00:00:00`),
  );
}

const degreeLevelLabels: Record<DegreeLevel, string> = {
  NONE: "Không có bằng thuộc danh mục",
  ASSOCIATE: "Cao đẳng",
  BACHELOR: "Cử nhân / Kỹ sư",
  MASTER: "Thạc sĩ",
  PHD: "Tiến sĩ",
};

function degreeLevelLabel(value: EducationDto["degree_level"]) {
  return value && value in degreeLevelLabels
    ? degreeLevelLabels[value as DegreeLevel]
    : "Chưa xác định bậc học vấn";
}

export function EducationSection({
  items,
  pending,
  onChange,
}: {
  items: EducationDto[];
  pending: boolean;
  onChange: (items: EducationDto[]) => void;
}) {
  const [formOpen, setFormOpen] = useState(false);
  const [editing, setEditing] = useState<EducationDto | null>(null);
  const [formError, setFormError] = useState<string | null>(null);

  const closeForm = () => {
    setFormOpen(false);
    setEditing(null);
    setFormError(null);
  };

  const submit = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const degreeLevel = String(form.get("degree_level") ?? "");
    const isCompleted = form.get("is_completed") === "on";
    const isVerified = form.get("is_verified") === "on";
    if (isVerified && (!isCompleted || !degreeLevel)) {
      setFormError("Chỉ có thể xác nhận khi học vấn đã hoàn thành và đã chọn bậc học vấn.");
      return;
    }
    setFormError(null);
    const payload: EducationPayload = {
      school_name: String(form.get("school_name") ?? "").trim(),
      major: String(form.get("major") ?? "").trim(),
      degree: String(form.get("degree") ?? "").trim(),
      degree_level: degreeLevel ? degreeLevel as DegreeLevel : null,
      is_completed: isCompleted,
      is_verified: isVerified,
      start_date: String(form.get("start_date") ?? "") || null,
      end_date: String(form.get("end_date") ?? "") || null,
      description: String(form.get("description") ?? "").trim(),
    };
    const now = new Date().toISOString();
    const item: EducationDto = {
      id: editing?.id ?? crypto.randomUUID(),
      ...payload,
      created_at: editing?.created_at ?? now,
      updated_at: now,
    };
    onChange(editing ? items.map((current) => current.id === editing.id ? item : current) : [...items, item]);
    closeForm();
  };

  const remove = (item: EducationDto) => {
    if (!window.confirm(`Xóa học vấn tại ${item.school_name}?`)) return;
    onChange(items.filter((current) => current.id !== item.id));
  };

  return (
    <ProfileSection
      id="education"
      icon={GraduationCap}
      title="Học vấn"
      description="Nền tảng học tập và chuyên ngành liên quan."
      action={
        !formOpen ? (
          <Button type="button" variant="outline" size="sm" onClick={() => setFormOpen(true)}>
            <Plus />
            <span className="hidden sm:inline">Thêm</span>
          </Button>
        ) : undefined
      }
    >
      {formOpen && (
        <form onSubmit={submit} className="mb-6 space-y-4 rounded-xl border border-primary-100 bg-primary-50/40 p-4">
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="sm:col-span-2">
              <FieldLabel htmlFor="education-school">Trường / cơ sở đào tạo *</FieldLabel>
              <Input
                id="education-school"
                name="school_name"
                defaultValue={editing?.school_name}
                required
              />
            </div>
            <div>
              <FieldLabel htmlFor="education-major">Chuyên ngành</FieldLabel>
              <Input id="education-major" name="major" defaultValue={editing?.major} />
            </div>
            <div>
              <FieldLabel htmlFor="education-degree">Bằng cấp</FieldLabel>
              <Input id="education-degree" name="degree" defaultValue={editing?.degree} />
            </div>
            <div>
              <FieldLabel htmlFor="education-degree-level">Bậc học vấn chuẩn hóa</FieldLabel>
              <select
                id="education-degree-level"
                name="degree_level"
                defaultValue={editing?.degree_level ?? ""}
                className="h-10 w-full rounded-md border border-zinc-300 bg-white px-3 text-sm outline-none focus:border-primary"
              >
                <option value="">Chưa xác định</option>
                {Object.entries(degreeLevelLabels).map(([value, label]) => (
                  <option key={value} value={value}>{label}</option>
                ))}
              </select>
              <p className="mt-1 text-xs leading-5 text-zinc-500">
                “Chưa xác định” khác với “Không có bằng thuộc danh mục”.
              </p>
            </div>
            <div>
              <FieldLabel htmlFor="education-start">Bắt đầu</FieldLabel>
              <Input
                id="education-start"
                name="start_date"
                type="date"
                defaultValue={editing?.start_date ?? ""}
              />
            </div>
            <div>
              <FieldLabel htmlFor="education-end">Kết thúc</FieldLabel>
              <Input
                id="education-end"
                name="end_date"
                type="date"
                defaultValue={editing?.end_date ?? ""}
              />
            </div>
          </div>
          <div className="grid gap-3 rounded-xl border border-zinc-200 bg-white p-3 sm:grid-cols-2">
            <label className="flex items-start gap-2 text-sm text-zinc-700">
              <input
                name="is_completed"
                type="checkbox"
                defaultChecked={editing?.is_completed ?? false}
                className="mt-0.5 size-4 accent-primary"
              />
              <span><span className="font-medium">Đã hoàn thành</span><span className="mt-0.5 block text-xs text-zinc-500">Chương trình học hoặc bằng cấp này đã hoàn tất.</span></span>
            </label>
            <label className="flex items-start gap-2 text-sm text-zinc-700">
              <input
                name="is_verified"
                type="checkbox"
                defaultChecked={editing?.is_verified ?? false}
                className="mt-0.5 size-4 accent-primary"
              />
              <span><span className="font-medium">Tôi xác nhận thông tin này</span><span className="mt-0.5 block text-xs text-zinc-500">Chỉ xác nhận khi đã hoàn thành và đã chọn bậc học vấn.</span></span>
            </label>
          </div>
          <div>
            <FieldLabel htmlFor="education-description">Mô tả</FieldLabel>
            <textarea
              id="education-description"
              name="description"
              defaultValue={editing?.description}
              className={textareaClassName}
              placeholder="Thành tích, môn học hoặc dự án nổi bật..."
            />
          </div>
          {formError && <p className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">{formError}</p>}
          <div className="flex justify-end gap-2">
            <Button type="button" variant="ghost" onClick={closeForm} disabled={pending}>Hủy</Button>
            <Button type="submit" disabled={pending}>{pending ? "Đang lưu..." : "Lưu học vấn"}</Button>
          </div>
        </form>
      )}

      {!items.length ? (
        <EmptySection>Thêm học vấn để nhà tuyển dụng hiểu rõ nền tảng của bạn.</EmptySection>
      ) : (
        <div className="space-y-0">
          {items.map((item, index) => (
            <div key={item.id} className="relative flex gap-4 pb-6 last:pb-0">
              {index < items.length - 1 && <span className="absolute left-2 top-5 h-full w-px bg-zinc-200" />}
              <span className="relative mt-1 size-4 shrink-0 rounded-full border-4 border-primary-100 bg-primary" />
              <div className="min-w-0 flex-1">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <h3 className="font-semibold text-zinc-900">{item.school_name}</h3>
                    <p className="mt-1 text-sm text-zinc-600">
                      {[item.degree, item.major].filter(Boolean).join(" · ") || "Chưa cập nhật ngành học"}
                    </p>
                    <p className="mt-1 text-xs text-zinc-500">
                      {degreeLevelLabel(item.degree_level)} · {item.is_completed ? "Đã hoàn thành" : "Chưa hoàn thành"} · {item.is_verified ? "Ứng viên đã xác nhận" : "Chưa được ứng viên xác nhận"}
                    </p>
                    <p className="mt-1 text-xs font-medium text-zinc-400">
                      {formatDate(item.start_date, "Chưa cập nhật")} – {formatDate(item.end_date)}
                    </p>
                  </div>
                  <div className="flex shrink-0">
                    <Button
                      type="button"
                      variant="ghost"
                      size="icon"
                      aria-label="Sửa học vấn"
                      onClick={() => {
                        setEditing(item);
                        setFormOpen(true);
                      }}
                    >
                      <Pencil />
                    </Button>
                    <Button
                      type="button"
                      variant="ghost"
                      size="icon"
                      className="text-red-500 hover:bg-red-50 hover:text-red-600"
                      aria-label="Xóa học vấn"
                      onClick={() => remove(item)}
                    >
                      <Trash2 />
                    </Button>
                  </div>
                </div>
                {item.description && <p className="mt-3 text-sm leading-6 text-zinc-600">{item.description}</p>}
              </div>
            </div>
          ))}
        </div>
      )}
    </ProfileSection>
  );
}
