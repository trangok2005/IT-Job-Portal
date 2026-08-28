"use client";

import { GitMerge, Plus, Scale, Sparkles, Tags } from "lucide-react";
import { useEffect, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  createAdminSkill,
  createSkillCategory,
  createWeightConfig,
  getAdminSkills,
  getSkillCategories,
  getWeightConfigs,
  mergeSkills,
  reviewSkill,
  updateAdminSkill,
  updateWeightConfig,
} from "@/features/admin/api";
import type {
  AdminSkillDto,
  AdminSkillQuery,
  SkillCategoryDto,
  WeightConfigDto,
  WeightConfigPayload,
} from "@/features/admin/types";

type Tab = "taxonomy" | "weights";

const fieldClass =
  "h-11 w-full rounded-xl border border-zinc-300 bg-white px-3.5 text-sm outline-none focus:border-primary";

export function SkillsAdmin() {
  const [tab, setTab] = useState<Tab>("taxonomy");
  const [skills, setSkills] = useState<AdminSkillDto[]>([]);
  const [approvedSkills, setApprovedSkills] = useState<AdminSkillDto[]>([]);
  const [categories, setCategories] = useState<SkillCategoryDto[]>([]);
  const [configs, setConfigs] = useState<WeightConfigDto[]>([]);
  const [status, setStatus] = useState<AdminSkillQuery["status"] | "">("");
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([
      getAdminSkills(),
      getAdminSkills({ status: "APPROVED" }),
      getSkillCategories(),
      getWeightConfigs(),
    ])
      .then(([skillResponse, approvedResponse, categoryResponse, configResponse]) => {
        setSkills(skillResponse.results);
        setApprovedSkills(approvedResponse.results);
        setCategories(categoryResponse.results);
        setConfigs(configResponse.results);
      })
      .catch((reason: unknown) => {
        setError(reason instanceof Error ? reason.message : "Không thể tải dữ liệu skill.");
      })
      .finally(() => setLoading(false));
  }, []);

  const refreshSkills = async (nextStatus = status) => {
    const response = await getAdminSkills({ status: nextStatus || undefined });
    setSkills(response.results);
  };

  const refreshApprovedSkills = async () => {
    const response = await getAdminSkills({ status: "APPROVED" });
    setApprovedSkills(response.results);
  };

  const refreshConfigs = async () => {
    const response = await getWeightConfigs();
    setConfigs(response.results);
  };

  const run = async (key: string, success: string, action: () => Promise<unknown>) => {
    setBusy(key);
    setError(null);
    setNotice(null);
    try {
      await action();
      setNotice(success);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Thao tác không thành công.");
    } finally {
      setBusy(null);
    }
  };

  const createSkill = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const form = event.currentTarget;
    const data = new FormData(form);
    const aliases = String(data.get("aliases") ?? "")
      .split(",")
      .map((value) => value.trim())
      .filter(Boolean);
    await run("create-skill", "Đã tạo skill chuẩn hóa.", async () => {
      await createAdminSkill({
        name: String(data.get("name") ?? "").trim(),
        category: String(data.get("category") ?? "") || null,
        aliases,
        is_active: true,
      });
      form.reset();
      await refreshSkills();
    });
  };

  const createCategory = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const form = event.currentTarget;
    const data = new FormData(form);
    await run("create-category", "Đã tạo nhóm skill.", async () => {
      await createSkillCategory({ name: String(data.get("name") ?? "").trim() });
      const response = await getSkillCategories();
      setCategories(response.results);
      form.reset();
    });
  };

  const merge = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const form = event.currentTarget;
    const data = new FormData(form);
    const sourceId = String(data.get("source_id") ?? "");
    const targetId = String(data.get("target_id") ?? "");
    if (!sourceId || !targetId || sourceId === targetId) {
      setError("Skill nguồn và skill đích phải khác nhau.");
      return;
    }
    if (!window.confirm("Merge sẽ chuyển toàn bộ liên kết sang skill đích và không thể đảo ngược. Tiếp tục?")) return;
    await run("merge", "Đã gộp skill trùng.", async () => {
      await mergeSkills({ source_ids: [sourceId], target_id: targetId });
      form.reset();
      await Promise.all([refreshSkills(), refreshApprovedSkills()]);
    });
  };

  const createConfig = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const form = event.currentTarget;
    const data = new FormData(form);
    const payload: WeightConfigPayload = {
      name: String(data.get("name") ?? "").trim(),
      weight_semantic_similarity: String(data.get("semantic") ?? ""),
      weight_skill_overlap: String(data.get("skill") ?? ""),
      weight_experience_match: String(data.get("experience") ?? ""),
      weight_education_match: String(data.get("education") ?? ""),
      is_active: data.get("is_active") === "on",
    };
    const total = [
      payload.weight_semantic_similarity,
      payload.weight_skill_overlap,
      payload.weight_experience_match,
      payload.weight_education_match,
    ].reduce((sum, value) => sum + Number(value), 0);
    if (Math.abs(total - 1) > 0.001) {
      setError(`Tổng trọng số hiện là ${total.toFixed(3)}, yêu cầu bằng 1.000.`);
      return;
    }
    await run("create-config", "Đã lưu cấu hình trọng số.", async () => {
      await createWeightConfig(payload);
      form.reset();
      await refreshConfigs();
    });
  };

  return (
    <div className="mx-auto max-w-6xl px-4 py-7 sm:px-6 lg:px-8">
      <div className="flex items-start gap-3">
        <span className="grid size-11 place-items-center rounded-xl bg-primary text-white">
          <Sparkles className="size-5" />
        </span>
        <div>
          <h1 className="text-2xl font-bold text-zinc-900">Skill Taxonomy & Ranking</h1>
          <p className="mt-1 text-sm text-zinc-500">Chuẩn hóa kỹ năng và điều chỉnh tín hiệu xếp hạng AI.</p>
        </div>
      </div>

      <div className="mt-6 inline-flex rounded-xl border border-zinc-200 bg-white p-1 shadow-sm">
        <button type="button" onClick={() => setTab("taxonomy")} className={`rounded-lg px-4 py-2 text-sm font-medium ${tab === "taxonomy" ? "bg-primary text-white" : "text-zinc-600"}`}>Skill taxonomy</button>
        <button type="button" onClick={() => setTab("weights")} className={`rounded-lg px-4 py-2 text-sm font-medium ${tab === "weights" ? "bg-primary text-white" : "text-zinc-600"}`}>Trọng số matching</button>
      </div>

      {error && <p className="mt-4 rounded-xl bg-red-50 p-4 text-sm text-red-700">{error}</p>}
      {notice && <p className="mt-4 rounded-xl bg-emerald-50 p-4 text-sm text-emerald-700">{notice}</p>}
      {loading && <div className="mt-6 h-56 animate-pulse rounded-xl bg-zinc-100" />}

      {!loading && tab === "taxonomy" && (
        <div className="mt-6 space-y-6">
          <div className="grid gap-4 lg:grid-cols-2">
            <form onSubmit={createSkill} className="rounded-xl border border-zinc-200 bg-white p-5 shadow-sm">
              <div className="flex items-center gap-2"><Plus className="size-4 text-primary" /><h2 className="font-semibold text-zinc-900">Tạo skill chuẩn</h2></div>
              <div className="mt-4 grid gap-3 sm:grid-cols-2">
                <Input name="name" placeholder="Tên skill, ví dụ React" required />
                <select name="category" className={fieldClass}><option value="">Không phân nhóm</option>{categories.map((category) => <option key={category.id} value={category.id}>{category.name}</option>)}</select>
                <Input name="aliases" className="sm:col-span-2" placeholder="Alias cách nhau bằng dấu phẩy: ReactJS, React.js" />
              </div>
              <Button className="mt-4" size="sm" disabled={busy === "create-skill"}>{busy === "create-skill" ? "Đang tạo..." : "Tạo skill"}</Button>
            </form>

            <form onSubmit={createCategory} className="rounded-xl border border-zinc-200 bg-white p-5 shadow-sm">
              <div className="flex items-center gap-2"><Tags className="size-4 text-accent" /><h2 className="font-semibold text-zinc-900">Nhóm kỹ năng</h2></div>
              <div className="mt-4 flex gap-2"><Input name="name" placeholder="Backend, Frontend, DevOps..." required /><Button size="sm" disabled={busy === "create-category"}>Thêm nhóm</Button></div>
              <div className="mt-4 flex flex-wrap gap-2">{categories.map((category) => <Badge key={category.id} variant="outline">{category.name} · {category.skill_count}</Badge>)}</div>
            </form>
          </div>

          <form onSubmit={merge} className="rounded-xl border border-amber-200 bg-amber-50/50 p-5">
            <div className="flex items-center gap-2"><GitMerge className="size-4 text-amber-700" /><h2 className="font-semibold text-zinc-900">Gộp skill trùng</h2></div>
            <p className="mt-1 text-xs text-zinc-500">Mọi hồ sơ và tin tuyển dụng sẽ được chuyển từ skill nguồn sang skill đích.</p>
            <div className="mt-4 grid gap-2 sm:grid-cols-[1fr_auto_1fr_auto] sm:items-center">
              <select name="source_id" className={fieldClass} required><option value="">Skill nguồn</option>{skills.filter((skill) => skill.status !== "MERGED").map((skill) => <option key={skill.id} value={skill.id}>{skill.name}</option>)}</select>
              <span className="hidden text-zinc-400 sm:block">→</span>
              <select name="target_id" className={fieldClass} required><option value="">Skill đích</option>{approvedSkills.map((skill) => <option key={skill.id} value={skill.id}>{skill.name}</option>)}</select>
              <Button variant="outline" disabled={busy === "merge"}>Merge</Button>
            </div>
          </form>

          <section>
            <div className="flex flex-col justify-between gap-3 sm:flex-row sm:items-center">
              <div><h2 className="font-semibold text-zinc-900">Danh sách skill</h2><p className="text-xs text-zinc-500">{skills.length} kết quả trong bộ lọc hiện tại</p></div>
              <select value={status} onChange={(event) => { const value = event.target.value as typeof status; setStatus(value); void run("filter", "", () => refreshSkills(value)); }} className="h-10 rounded-xl border border-zinc-300 bg-white px-3 text-sm"><option value="">Tất cả</option><option value="PENDING">Chờ duyệt</option><option value="APPROVED">Đã duyệt</option><option value="REJECTED">Từ chối</option><option value="MERGED">Đã merge</option></select>
            </div>
            <div className="mt-3 overflow-hidden rounded-xl border border-zinc-200 bg-white shadow-sm">
              {skills.length === 0 && <p className="p-10 text-center text-sm text-zinc-500">Không có skill trong trạng thái này.</p>}
              {skills.map((skill) => (
                <div key={skill.id} className="flex flex-col gap-3 border-b border-zinc-100 p-4 last:border-0 sm:flex-row sm:items-center">
                  <div className="min-w-0 flex-1"><div className="flex flex-wrap items-center gap-2"><p className="font-semibold text-zinc-900">{skill.name}</p><Badge variant={skill.status === "APPROVED" ? "success" : "outline"}>{skill.status}</Badge>{!skill.is_active && <Badge variant="outline">Ẩn</Badge>}</div><p className="mt-1 text-xs text-zinc-500">{skill.category_name || "Chưa phân nhóm"} · {skill.source}{skill.aliases.length > 0 && ` · Alias: ${skill.aliases.map((alias) => alias.alias_text).join(", ")}`}</p>{skill.merged_into_name && <p className="mt-1 text-xs text-amber-700">Đã gộp vào {skill.merged_into_name}</p>}</div>
                  <div className="flex flex-wrap gap-2">
                    {skill.status === "PENDING" && <><Button size="sm" variant="outline" disabled={busy === skill.id} onClick={() => void run(skill.id, "Đã từ chối skill.", async () => { await reviewSkill(skill.id, "reject"); await refreshSkills(); })}>Từ chối</Button><Button size="sm" disabled={busy === skill.id} onClick={() => void run(skill.id, "Đã duyệt skill.", async () => { await reviewSkill(skill.id, "approve"); await Promise.all([refreshSkills(), refreshApprovedSkills()]); })}>Duyệt</Button></>}
                    {skill.status === "APPROVED" && <Button size="sm" variant="outline" disabled={busy === skill.id} onClick={() => void run(skill.id, skill.is_active ? "Đã ẩn skill." : "Đã kích hoạt skill.", async () => { await updateAdminSkill(skill.id, { is_active: !skill.is_active }); await refreshSkills(); })}>{skill.is_active ? "Ẩn" : "Kích hoạt"}</Button>}
                  </div>
                </div>
              ))}
            </div>
          </section>
        </div>
      )}

      {!loading && tab === "weights" && (
        <div className="mt-6 grid gap-5 lg:grid-cols-[minmax(0,1fr)_360px]">
          <section className="space-y-3">
            <div><h2 className="font-semibold text-zinc-900">Các phiên bản cấu hình</h2><p className="mt-1 text-xs text-zinc-500">Chỉ một cấu hình được kích hoạt tại một thời điểm.</p></div>
            {configs.map((config) => (
              <article key={config.id} className={`rounded-xl border bg-white p-5 shadow-sm ${config.is_active ? "border-emerald-300 ring-2 ring-emerald-100" : "border-zinc-200"}`}>
                <div className="flex items-start justify-between gap-3"><div><div className="flex items-center gap-2"><h3 className="font-semibold text-zinc-900">{config.name}</h3>{config.is_active && <Badge variant="success">Đang áp dụng</Badge>}</div><p className="mt-1 text-xs text-zinc-400">Cập nhật {new Date(config.updated_at).toLocaleString("vi-VN")}</p></div>{!config.is_active && <Button size="sm" variant="outline" disabled={busy === config.id} onClick={() => void run(config.id, "Đã kích hoạt cấu hình.", async () => { await updateWeightConfig(config.id, { is_active: true }); await refreshConfigs(); })}>Kích hoạt</Button>}</div>
                <div className="mt-4 grid grid-cols-2 gap-2 text-xs sm:grid-cols-4"><Weight label="Semantic" value={config.weight_semantic_similarity} /><Weight label="Skill" value={config.weight_skill_overlap} /><Weight label="Kinh nghiệm" value={config.weight_experience_match} /><Weight label="Học vấn" value={config.weight_education_match} /></div>
              </article>
            ))}
          </section>

          <form onSubmit={createConfig} className="h-fit rounded-xl border border-zinc-200 bg-white p-5 shadow-sm">
            <div className="flex items-center gap-2"><Scale className="size-4 text-primary" /><h2 className="font-semibold text-zinc-900">Cấu hình mới</h2></div>
            <p className="mt-1 text-xs text-zinc-500">Tổng bốn trọng số phải bằng 1.000.</p>
            <div className="mt-4 space-y-3"><Input name="name" placeholder="Tên phiên bản" required /><WeightInput name="semantic" label="Semantic similarity" defaultValue="0.600" /><WeightInput name="skill" label="Skill overlap" defaultValue="0.250" /><WeightInput name="experience" label="Experience match" defaultValue="0.100" /><WeightInput name="education" label="Education match" defaultValue="0.050" /><label className="flex items-center gap-2 text-sm text-zinc-600"><input type="checkbox" name="is_active" className="size-4 accent-primary" />Kích hoạt ngay</label></div>
            <Button className="mt-4 w-full" disabled={busy === "create-config"}>{busy === "create-config" ? "Đang lưu..." : "Lưu cấu hình"}</Button>
          </form>
        </div>
      )}
    </div>
  );
}

function Weight({ label, value }: { label: string; value?: string }) {
  return <div className="rounded-lg bg-zinc-50 p-2.5"><p className="text-zinc-400">{label}</p><p className="mt-1 font-semibold text-zinc-800">{Number(value ?? 0).toFixed(3)}</p></div>;
}

function WeightInput({ name, label, defaultValue }: { name: string; label: string; defaultValue: string }) {
  return <label className="block text-xs font-medium text-zinc-600">{label}<Input name={name} type="number" min="0" max="1" step="0.001" defaultValue={defaultValue} className="mt-1" required /></label>;
}
