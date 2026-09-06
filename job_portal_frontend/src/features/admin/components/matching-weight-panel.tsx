"use client";

import { useEffect, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  createWeightConfig,
  getActiveWeightConfig,
  updateWeightConfig,
} from "@/features/admin/api";
import type {
  WeightConfigDto,
  WeightConfigPayload,
} from "@/features/admin/types";
import { ApiError } from "@/lib/api-client";

type WeightDraft = {
  name: string;
  semantic: string;
  skill: string;
  experience: string;
  education: string;
  multiplier: string;
};

type WeightKey = "semantic" | "skill" | "experience" | "education";

const WEIGHT_FIELDS: Array<{ key: WeightKey; label: string }> = [
  { key: "semantic", label: "Ngữ nghĩa" },
  { key: "skill", label: "Kỹ năng" },
  { key: "experience", label: "Kinh nghiệm" },
  { key: "education", label: "Học vấn" },
];

const EMPTY_DRAFT: WeightDraft = {
  name: "",
  semantic: "",
  skill: "",
  experience: "",
  education: "",
  multiplier: "",
};

function draftFromConfig(config: WeightConfigDto): WeightDraft {
  return {
    name: config.name,
    semantic: String(Number((Number(config.weight_semantic_similarity) * 100).toFixed(1))),
    skill: String(Number((Number(config.weight_skill_overlap) * 100).toFixed(1))),
    experience: String(Number((Number(config.weight_experience_match) * 100).toFixed(1))),
    education: String(Number((Number(config.weight_education_match) * 100).toFixed(1))),
    multiplier: String(config.required_skill_multiplier),
  };
}

function validateDraft(draft: WeightDraft) {
  const errors: Partial<Record<keyof WeightDraft, string>> = {};
  const values = WEIGHT_FIELDS.map(({ key }) => Number(draft[key]));
  WEIGHT_FIELDS.forEach(({ key }, index) => {
    if (draft[key].trim() === "" || !Number.isFinite(values[index])) {
      errors[key] = "Hãy nhập một số hợp lệ.";
    } else if (values[index] < 0 || values[index] > 100) {
      errors[key] = "Giá trị phải từ 0 đến 100%.";
    }
  });
  const multiplier = Number(draft.multiplier);
  if (!draft.name.trim()) errors.name = "Tên cấu hình không được để trống.";
  if (draft.multiplier.trim() === "" || !Number.isFinite(multiplier)) {
    errors.multiplier = "Hãy nhập một số hợp lệ.";
  } else if (multiplier < 1 || multiplier > 999.999) {
    errors.multiplier = "Hệ số phải từ 1 đến 999.999.";
  }
  const total = values.every(Number.isFinite)
    ? values.reduce((sum, value) => sum + value, 0)
    : Number.NaN;
  const decimalTotal = values.every(Number.isFinite)
    ? values.reduce((sum, value) => sum + Number((value / 100).toFixed(3)), 0)
    : Number.NaN;
  const totalValid = Number.isFinite(total)
    && Math.abs(total - 100) < 0.0001
    && Math.abs(decimalTotal - 1) < 0.0001;
  return { errors, total, totalValid, valid: Object.keys(errors).length === 0 && totalValid };
}

export function MatchingWeightPanel() {
  const [config, setConfig] = useState<WeightConfigDto | null>(null);
  const [draft, setDraft] = useState<WeightDraft | null>(null);
  const [baseline, setBaseline] = useState<WeightDraft | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [reloadKey, setReloadKey] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    getActiveWeightConfig(controller.signal)
      .then((result) => {
        const next = draftFromConfig(result);
        setConfig(result);
        setDraft(next);
        setBaseline(next);
      })
      .catch((reason: unknown) => {
        if (controller.signal.aborted) return;
        if (reason instanceof ApiError && reason.status === 404) {
          setConfig(null);
          setDraft(EMPTY_DRAFT);
          setBaseline(EMPTY_DRAFT);
          return;
        }
        setLoadError(reason instanceof Error ? reason.message : "Không thể tải cấu hình trọng số.");
      })
      .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [reloadKey]);

  if (loading) return <WeightSkeleton />;
  if (loadError || !draft || !baseline) {
    return (
      <section className="rounded-2xl border border-red-200 bg-red-50 p-6 text-center" role="alert">
        <h2 className="font-semibold text-red-800">Không thể tải cấu hình</h2>
        <p className="mt-2 text-sm text-red-700">{loadError}</p>
        <Button type="button" variant="outline" size="sm" className="mt-4" onClick={() => { setLoading(true); setLoadError(null); setReloadKey((value) => value + 1); }}>Thử lại</Button>
      </section>
    );
  }

  const validation = validateDraft(draft);
  const changed = JSON.stringify(draft) !== JSON.stringify(baseline);
  const update = (key: keyof WeightDraft, value: string) => {
    setDraft((current) => current ? { ...current, [key]: value } : current);
    setSaveError(null);
    setNotice(null);
  };
  const reset = () => {
    setDraft({ ...baseline });
    setSaveError(null);
    setNotice(null);
  };
  const save = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!validation.valid || !changed || saving) return;
    const payload: WeightConfigPayload = {
      name: draft.name.trim(),
      weight_semantic_similarity: (Number(draft.semantic) / 100).toFixed(3),
      weight_skill_overlap: (Number(draft.skill) / 100).toFixed(3),
      weight_experience_match: (Number(draft.experience) / 100).toFixed(3),
      weight_education_match: (Number(draft.education) / 100).toFixed(3),
      required_skill_multiplier: Number(draft.multiplier).toFixed(3),
      is_active: true,
    };
    setSaving(true);
    setSaveError(null);
    setNotice(null);
    try {
      const saved = config
        ? await updateWeightConfig(config.id, payload)
        : await createWeightConfig(payload);
      const next = draftFromConfig(saved);
      setConfig(saved);
      setDraft(next);
      setBaseline(next);
      setNotice("Đã lưu cấu hình trọng số đang hoạt động.");
    } catch (reason) {
      setSaveError(reason instanceof Error ? reason.message : "Không thể lưu cấu hình trọng số.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <form onSubmit={save} className="space-y-5">
      <section className="rounded-2xl border border-zinc-200 bg-white p-5 shadow-sm">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div><h2 className="font-semibold text-zinc-900">Cấu hình trọng số so khớp</h2><p className="mt-1 text-xs text-zinc-500">Chỉnh cấu hình đang được hệ thống sử dụng.</p></div>
          {config ? <Badge variant="success">Đang hoạt động</Badge> : <Badge variant="outline">Chưa có cấu hình</Badge>}
        </div>
        <label className="mt-5 block text-sm font-medium text-zinc-700">Tên cấu hình<Input value={draft.name} onChange={(event) => update("name", event.target.value)} className="mt-1.5" maxLength={150} aria-invalid={Boolean(validation.errors.name)} /></label>
        {validation.errors.name && <p className="mt-1 text-xs text-red-600">{validation.errors.name}</p>}
        <div className="mt-5 space-y-4">
          {WEIGHT_FIELDS.map(({ key, label }) => {
            const numericValue = Number(draft[key]);
            const progress = Number.isFinite(numericValue) ? Math.max(0, Math.min(100, numericValue)) : 0;
            return (
              <div key={key}>
                <label className="flex items-center justify-between gap-3 text-sm font-medium text-zinc-700"><span>{label}</span><span className="relative w-28"><Input type="number" min="0" max="100" step="0.1" value={draft[key]} onChange={(event) => update(key, event.target.value)} className="h-10 pr-8 text-right" aria-invalid={Boolean(validation.errors[key])} /><span className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 text-xs text-zinc-400">%</span></span></label>
                <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-zinc-100"><div className="h-full rounded-full bg-primary" style={{ width: `${progress}%` }} /></div>
                {validation.errors[key] && <p className="mt-1 text-xs text-red-600">{validation.errors[key]}</p>}
              </div>
            );
          })}
        </div>
        <div className={`mt-5 rounded-xl border p-3 text-sm ${validation.totalValid ? "border-emerald-200 bg-emerald-50 text-emerald-700" : "border-red-200 bg-red-50 text-red-700"}`}>
          <p className="font-semibold">Tổng trọng số: {Number.isFinite(validation.total) ? `${validation.total.toFixed(1)}%` : "—"}</p>
          {!validation.totalValid && <p className="mt-1 text-xs">Tổng bốn trọng số phải bằng 100%.</p>}
        </div>
      </section>

      <section className="rounded-2xl border border-zinc-200 bg-white p-5 shadow-sm">
        <h2 className="font-semibold text-zinc-900">Hệ số kỹ năng bắt buộc</h2>
        <label className="mt-4 block text-sm font-medium text-zinc-700">Giá trị hệ số<Input type="number" min="1" max="999.999" step="0.001" value={draft.multiplier} onChange={(event) => update("multiplier", event.target.value)} className="mt-1.5" aria-invalid={Boolean(validation.errors.multiplier)} /></label>
        {validation.errors.multiplier && <p className="mt-1 text-xs text-red-600">{validation.errors.multiplier}</p>}
        <p className="mt-4 text-xs leading-5 text-zinc-500">Hệ số này làm tăng mức đóng góp của các kỹ năng được đánh dấu là bắt buộc trong tin tuyển dụng. Giá trị càng lớn thì kỹ năng bắt buộc càng có ảnh hưởng đến điểm kỹ năng.</p>
        <p className="mt-2 text-xs leading-5 text-zinc-500">Điểm phù hợp chỉ mang tính tham khảo; quyết định tuyển dụng thuộc về nhà tuyển dụng.</p>
        {saveError && <p className="mt-4 rounded-lg bg-red-50 p-3 text-sm text-red-700" role="alert">{saveError}</p>}
        {notice && <p className="mt-4 rounded-lg bg-emerald-50 p-3 text-sm text-emerald-700">{notice}</p>}
        <div className="mt-5 grid grid-cols-2 gap-2"><Button type="button" variant="outline" onClick={reset} disabled={!changed || saving}>Hủy thay đổi</Button><Button disabled={!validation.valid || !changed || saving}>{saving ? "Đang lưu..." : "Lưu cấu hình"}</Button></div>
      </section>
    </form>
  );
}

function WeightSkeleton() {
  return (
    <div className="space-y-5" aria-label="Đang tải cấu hình trọng số" aria-busy="true">
      <div className="h-[430px] animate-pulse rounded-2xl border border-zinc-200 bg-zinc-100" />
      <div className="h-64 animate-pulse rounded-2xl border border-zinc-200 bg-zinc-100" />
    </div>
  );
}
