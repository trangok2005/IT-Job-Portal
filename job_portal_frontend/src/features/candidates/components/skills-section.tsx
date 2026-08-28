"use client";

import { Pencil, Plus, Search, Sparkles, Trash2 } from "lucide-react";
import { useDeferredValue, useEffect, useEffectEvent, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { getSkillOptions } from "@/features/candidates/api";
import type {
  CandidateSkillDto,
  CandidateSkillPayload,
  SkillOptionDto,
} from "@/features/candidates/types";
import {
  EmptySection,
  FieldLabel,
  ProfileSection,
  fieldClassName,
} from "@/features/candidates/components/profile-section";

type SkillLevel = Exclude<CandidateSkillDto["level"], undefined>;

const levelLabels: Record<SkillLevel, string> = {
  "": "Chưa đánh giá",
  BASIC: "Cơ bản",
  INTERMEDIATE: "Trung bình",
  ADVANCED: "Nâng cao",
  EXPERT: "Chuyên gia",
};

export function SkillsSection({
  items,
  pending,
  onChange,
  previewSkillNames = [],
}: {
  items: CandidateSkillDto[];
  pending: boolean;
  onChange: (items: CandidateSkillDto[]) => void;
  previewSkillNames?: string[];
}) {
  const [options, setOptions] = useState<SkillOptionDto[]>([]);
  const [optionsError, setOptionsError] = useState<string | null>(null);
  const [unmatchedPreviewSkills, setUnmatchedPreviewSkills] = useState<string[]>([]);
  const [formOpen, setFormOpen] = useState(false);
  const [editing, setEditing] = useState<CandidateSkillDto | null>(null);
  const [search, setSearch] = useState("");
  const deferredSearch = useDeferredValue(search);

  const applyPreviewSkills = useEffectEvent((skillOptions: SkillOptionDto[]) => {
    if (!previewSkillNames.length) return;
    const names = new Set(previewSkillNames.map((name) => name.trim().toLowerCase()));
    const availableNames = new Set(skillOptions.map((option) => option.name.toLowerCase()));
    const unmatched = previewSkillNames.map((name) => name.trim()).filter(
      (name) => !availableNames.has(name.toLowerCase()),
    );
    setUnmatchedPreviewSkills(unmatched);
    const now = new Date().toISOString();
    const previewItems = skillOptions
      .filter((option) => names.has(option.name.toLowerCase()))
      .map<CandidateSkillDto>((option) => ({
        id: crypto.randomUUID(),
        skill: option.id,
        skill_name: option.name,
        skill_status: (option as { status?: string }).status ?? "APPROVED",
        level: "",
        years_of_experience: null,
        source: "AI_EXTRACTED",
        created_at: now,
        updated_at: now,
      }));
    const unmatchedItems = unmatched.map<CandidateSkillDto>((name) => ({
      id: crypto.randomUUID(),
      skill: name.trim(),
      skill_name: name.trim(),
      skill_status: "PENDING",
      level: "",
      years_of_experience: null,
      source: "AI_EXTRACTED",
      created_at: now,
      updated_at: now,
    }));
    if (previewItems.length || unmatchedItems.length) onChange([...previewItems, ...unmatchedItems]);
  });

  useEffect(() => {
    let active = true;
    getSkillOptions()
      .then((response) => {
        if (active) {
          setOptions(response.results);
          applyPreviewSkills(response.results);
        }
      })
      .catch((err: unknown) => {
        if (active) {
          setOptionsError(err instanceof Error ? err.message : "Không thể tải danh sách kỹ năng.");
        }
      });
    return () => {
      active = false;
    };
  }, []);

  const visibleOptions = options.filter((option) =>
    `${option.name} ${option.category_name}`.toLowerCase().includes(deferredSearch.toLowerCase()),
  );

  const openForm = (item?: CandidateSkillDto) => {
    setEditing(item ?? null);
    setSearch("");
    setFormOpen(true);
  };

  const closeForm = () => {
    setEditing(null);
    setFormOpen(false);
    setSearch("");
  };

  const submit = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const years = String(form.get("years_of_experience") ?? "").trim();
    const payload: CandidateSkillPayload = {
      skill: String(form.get("skill") ?? ""),
      level: String(form.get("level") ?? "") as SkillLevel,
      years_of_experience: years || null,
    };
    const now = new Date().toISOString();
    const option = options.find((item) => item.id === payload.skill);
    const item: CandidateSkillDto = {
      id: editing?.id ?? crypto.randomUUID(),
      ...payload,
      skill_name: option?.name ?? editing?.skill_name ?? "",
      skill_status: (option as { status?: string } | undefined)?.status
        ?? editing?.skill_status
        ?? "APPROVED",
      source: editing?.source ?? "MANUAL",
      created_at: editing?.created_at ?? now,
      updated_at: now,
    };
    onChange(
      editing
        ? items.map((current) => current.id === editing.id ? item : current)
        : [...items, item],
    );
    closeForm();
  };

  const remove = (item: CandidateSkillDto) => {
    if (!window.confirm(`Xóa kỹ năng ${item.skill_name}?`)) return;
    onChange(items.filter((current) => current.id !== item.id));
  };

  return (
    <ProfileSection
      id="skills"
      icon={Sparkles}
      title="Kỹ năng chuyên môn"
      description="Chọn kỹ năng chuẩn hóa để tăng độ chính xác khi AI matching."
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
          <div>
            <FieldLabel htmlFor="skill-search">Tìm kỹ năng</FieldLabel>
            <div className="relative">
              <Search className="absolute left-3.5 top-1/2 size-4 -translate-y-1/2 text-zinc-400" />
              <Input
                id="skill-search"
                value={search}
                onChange={(event) => setSearch(event.target.value)}
                className="pl-10"
                placeholder="Python, React, PostgreSQL..."
              />
            </div>
          </div>
          <div className="grid gap-4 sm:grid-cols-3">
            <div className="sm:col-span-3">
              <FieldLabel htmlFor="skill">Kỹ năng *</FieldLabel>
              <select
                id="skill"
                name="skill"
                defaultValue={editing?.skill ?? ""}
                className={fieldClassName}
                required
              >
                <option value="">Chọn kỹ năng</option>
                {visibleOptions.map((option) => (
                  <option key={option.id} value={option.id}>
                    {option.name}{option.category_name ? ` · ${option.category_name}` : ""}
                  </option>
                ))}
              </select>
              {optionsError && <p className="mt-1.5 text-xs text-red-600">{optionsError}</p>}
            </div>
            <div className="sm:col-span-2">
              <FieldLabel htmlFor="skill-level">Trình độ</FieldLabel>
              <select
                id="skill-level"
                name="level"
                defaultValue={editing?.level ?? ""}
                className={fieldClassName}
              >
                {Object.entries(levelLabels).map(([value, label]) => (
                  <option key={value || "empty"} value={value}>{label}</option>
                ))}
              </select>
            </div>
            <div>
              <FieldLabel htmlFor="skill-years">Số năm</FieldLabel>
              <Input
                id="skill-years"
                name="years_of_experience"
                type="number"
                min="0"
                step="0.5"
                defaultValue={editing?.years_of_experience ?? ""}
              />
            </div>
          </div>
          <div className="flex justify-end gap-2">
            <Button type="button" variant="ghost" onClick={closeForm} disabled={pending}>Hủy</Button>
            <Button type="submit" disabled={pending}>{pending ? "Đang lưu..." : "Lưu kỹ năng"}</Button>
          </div>
        </form>
      )}

      {unmatchedPreviewSkills.length > 0 && (
        <p className="mb-4 rounded-xl border border-amber-200 bg-amber-50 p-3 text-sm text-amber-800">
          Kỹ năng chưa chuẩn hóa: {unmatchedPreviewSkills.join(", ")}. Hệ thống sẽ tự chuẩn hóa khi bạn lưu hồ sơ.
        </p>
      )}

      {!items.length ? (
        <EmptySection>Thêm các kỹ năng bạn thực sự sử dụng để nhận gợi ý việc làm phù hợp hơn.</EmptySection>
      ) : (
        <div className="grid gap-3 sm:grid-cols-2">
          {items.map((item) => (
            <div key={item.id} className="flex items-center gap-3 rounded-xl border border-zinc-200 p-3.5 transition hover:border-primary-200">
              <span className="flex size-9 shrink-0 items-center justify-center rounded-xl bg-primary-50 text-sm font-bold text-primary">
                {item.skill_name.charAt(0).toUpperCase()}
              </span>
              <div className="min-w-0 flex-1">
                <div className="flex flex-wrap items-center gap-2">
                  <p className="truncate text-sm font-semibold text-zinc-900">{item.skill_name}</p>
                  {item.source === "AI_EXTRACTED" && <Badge>AI</Badge>}
                  {item.skill_status === "PENDING" && (
                    <Badge className="border-amber-200 bg-amber-50 text-amber-700">Chờ duyệt</Badge>
                  )}
                  {unmatchedPreviewSkills.includes(item.skill_name) && (
                    <Badge className="border-amber-200 bg-amber-50 text-amber-700">Chưa chuẩn hóa</Badge>
                  )}
                </div>
                <p className="mt-0.5 text-xs text-zinc-500">
                  {levelLabels[item.level ?? ""]}
                  {item.years_of_experience ? ` · ${item.years_of_experience} năm` : ""}
                </p>
              </div>
              <div className="flex shrink-0">
                <Button type="button" variant="ghost" size="icon" aria-label="Sửa kỹ năng" onClick={() => openForm(item)}>
                  <Pencil />
                </Button>
                <Button
                  type="button"
                  variant="ghost"
                  size="icon"
                  className="text-red-500 hover:bg-red-50 hover:text-red-600"
                  aria-label="Xóa kỹ năng"
                  onClick={() => remove(item)}
                >
                  <Trash2 />
                </Button>
              </div>
            </div>
          ))}
        </div>
      )}
    </ProfileSection>
  );
}
