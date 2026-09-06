"use client";

import { Plus } from "lucide-react";
import { useEffect, useEffectEvent, useRef, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  createAdminSkill,
  createSkillCategory,
  getAdminSkills,
  getSkillCategories,
  mergeSkills,
  reviewSkill,
  updateAdminSkill,
} from "@/features/admin/api";
import type { SkillsTab } from "@/features/admin/components/skills-admin";
import type {
  AdminSkillDto,
  SkillCategoryDto,
  SkillCreatePayload,
  SkillUpdatePayload,
} from "@/features/admin/types";
import { ApiError } from "@/lib/api-client";
import type { Paginated } from "@/lib/types";

const STATUS_LABELS: Record<AdminSkillDto["status"], string> = {
  PENDING: "Chờ duyệt",
  APPROVED: "Đã duyệt",
  REJECTED: "Đã từ chối",
  MERGED: "Đã hợp nhất",
};

const STATUS_CLASSES: Record<AdminSkillDto["status"], string> = {
  PENDING: "border-amber-200 bg-amber-50 text-amber-700",
  APPROVED: "border-emerald-200 bg-emerald-50 text-emerald-700",
  REJECTED: "border-red-200 bg-red-50 text-red-700",
  MERGED: "border-zinc-200 bg-zinc-100 text-zinc-600",
};

const TABS: Array<{ value: SkillsTab; label: string }> = [
  { value: "catalog", label: "Danh mục kỹ năng" },
  { value: "aliases", label: "Bí danh kỹ năng" },
  { value: "pending", label: "Kỹ năng chờ duyệt" },
];

type SkillListState = {
  requestKey: string;
  result: Paginated<AdminSkillDto> | null;
  error: string | null;
};

export function SkillManagementPanel({
  tab,
  status,
  page,
  onQueryChange,
}: {
  tab: SkillsTab;
  status: AdminSkillDto["status"] | "";
  page: number;
  onQueryChange: (changes: {
    tab?: SkillsTab;
    status?: AdminSkillDto["status"] | "";
    page?: number;
  }) => void;
}) {
  const [reloadKey, setReloadKey] = useState(0);
  const requestStatus = tab === "pending" ? "PENDING" : status;
  const requestKey = `${tab}|${requestStatus}|${page}|${reloadKey}`;
  const [state, setState] = useState<SkillListState>({
    requestKey: "",
    result: null,
    error: null,
  });
  const [notice, setNotice] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [skillForm, setSkillForm] = useState<AdminSkillDto | "new" | null>(null);
  const [categoryFormOpen, setCategoryFormOpen] = useState(false);
  const [mergeSource, setMergeSource] = useState<AdminSkillDto | null>(null);
  const loading = state.requestKey !== requestKey;
  const resetInvalidPage = useEffectEvent(() => onQueryChange({ page: 1 }));

  useEffect(() => {
    const controller = new AbortController();
    getAdminSkills(
      { page, status: requestStatus || undefined },
      controller.signal,
    )
      .then((result) => setState({ requestKey, result, error: null }))
      .catch((reason: unknown) => {
        if (controller.signal.aborted) return;
        if (reason instanceof ApiError && reason.status === 404 && page > 1) {
          resetInvalidPage();
          return;
        }
        setState({
          requestKey,
          result: null,
          error: reason instanceof Error ? reason.message : "Không thể tải danh sách kỹ năng.",
        });
      });
    return () => controller.abort();
  }, [page, requestKey, requestStatus]);

  const refresh = (message: string, resetPage = false) => {
    setNotice(message);
    if (resetPage && page > 1) onQueryChange({ page: 1 });
    else setReloadKey((value) => value + 1);
  };

  const review = async (skill: AdminSkillDto, action: "approve" | "reject") => {
    const verb = action === "approve" ? "duyệt" : "từ chối";
    if (!window.confirm(`Xác nhận ${verb} kỹ năng “${skill.name}”?`)) return;
    setBusyId(skill.id);
    setNotice(null);
    try {
      await reviewSkill(skill.id, action);
      refresh(action === "approve" ? "Đã duyệt kỹ năng." : "Đã từ chối kỹ năng.", true);
    } catch (reason) {
      setState((current) => ({
        ...current,
        error: reason instanceof Error ? reason.message : `Không thể ${verb} kỹ năng.`,
      }));
    } finally {
      setBusyId(null);
    }
  };

  return (
    <section className="min-w-0 overflow-hidden rounded-2xl border border-zinc-200 bg-white shadow-sm" aria-label="Quản lý kỹ năng">
      <div className="overflow-x-auto border-b border-zinc-200 px-4 sm:px-6">
        <div className="flex min-w-max gap-6" role="tablist" aria-label="Nhóm quản lý kỹ năng">
          {TABS.map((item) => (
            <button
              key={item.value}
              id={`skills-tab-${item.value}`}
              type="button"
              role="tab"
              aria-selected={tab === item.value}
              aria-controls="skills-panel"
              tabIndex={tab === item.value ? 0 : -1}
              onClick={() => onQueryChange({
                tab: item.value,
                status: item.value === "pending" ? "PENDING" : "",
                page: 1,
              })}
              className={`border-b-2 px-1 py-4 text-sm font-semibold transition-colors ${
                tab === item.value
                  ? "border-primary text-primary"
                  : "border-transparent text-zinc-500 hover:text-zinc-800"
              }`}
            >
              {item.label}
            </button>
          ))}
        </div>
      </div>

      <div id="skills-panel" role="tabpanel" aria-labelledby={`skills-tab-${tab}`} className="p-4 sm:p-6">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <h2 className="font-semibold text-zinc-900">{TABS.find((item) => item.value === tab)?.label}</h2>
            <p className="mt-1 text-xs text-zinc-500">
              {tab === "catalog" && "API hiện hỗ trợ lọc theo trạng thái; chưa hỗ trợ tìm kiếm hoặc lọc danh mục."}
              {tab === "aliases" && "Bí danh được cập nhật cùng kỹ năng chuẩn."}
              {tab === "pending" && "Chỉ kỹ năng đang chờ duyệt mới có thao tác kiểm duyệt và hợp nhất."}
            </p>
          </div>
          <div className="flex flex-col gap-2 sm:flex-row">
            {tab === "catalog" && (
              <label className="text-xs font-medium text-zinc-600">
                Trạng thái
                <select
                  value={status}
                  onChange={(event) => onQueryChange({
                    status: event.target.value as AdminSkillDto["status"] | "",
                    page: 1,
                  })}
                  className="mt-1 h-10 w-full rounded-xl border border-zinc-300 bg-white px-3 text-sm sm:w-40"
                >
                  <option value="">Tất cả</option>
                  {Object.entries(STATUS_LABELS).map(([value, label]) => <option key={value} value={value}>{label}</option>)}
                </select>
              </label>
            )}
            {tab === "catalog" && (
              <div className="flex items-end gap-2">
                <Button type="button" variant="outline" size="sm" onClick={() => setCategoryFormOpen(true)}>Thêm danh mục</Button>
                <Button type="button" size="sm" onClick={() => setSkillForm("new")}><Plus />Thêm kỹ năng</Button>
              </div>
            )}
          </div>
        </div>

        {notice && <p className="mt-4 rounded-xl border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-700" role="status">{notice}</p>}

        {loading ? (
          <SkillsSkeleton />
        ) : state.error ? (
          <div className="mt-5 rounded-xl border border-red-200 bg-red-50 p-6 text-center" role="alert">
            <p className="text-sm text-red-700">{state.error}</p>
            <Button type="button" variant="outline" size="sm" className="mt-4" onClick={() => setReloadKey((value) => value + 1)}>Thử lại</Button>
          </div>
        ) : state.result && state.result.results.length > 0 ? (
          <div className="mt-5 overflow-x-auto rounded-xl border border-zinc-200">
            <table className="w-full min-w-[720px] border-collapse text-left text-sm">
              <thead className="bg-zinc-50 text-xs uppercase tracking-wide text-zinc-500">
                <tr>
                  <th className="px-4 py-3 font-semibold">Tên kỹ năng</th>
                  <th className="px-4 py-3 font-semibold">Bí danh</th>
                  <th className="px-4 py-3 font-semibold">Danh mục</th>
                  {tab === "pending" && <th className="px-4 py-3 font-semibold">Ngày tạo</th>}
                  <th className="px-4 py-3 font-semibold">Trạng thái</th>
                  <th className="px-4 py-3 text-right font-semibold">Thao tác</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-zinc-100">
                {state.result.results.map((skill) => (
                  <tr key={skill.id} className="align-top hover:bg-zinc-50/70">
                    <td className="px-4 py-4">
                      <p className="font-semibold text-zinc-900">{skill.name}</p>
                      {!skill.is_active && <p className="mt-1 text-xs text-zinc-400">Đang ẩn</p>}
                    </td>
                    <td className="max-w-64 px-4 py-4">
                      <AliasBadges skill={skill} showAll={tab !== "catalog"} />
                    </td>
                    <td className="px-4 py-4 text-zinc-600">{skill.category_name || "Chưa phân nhóm"}</td>
                    {tab === "pending" && <td className="px-4 py-4 text-zinc-500">{new Date(skill.created_at).toLocaleDateString("vi-VN")}</td>}
                    <td className="px-4 py-4"><SkillStatusBadge status={skill.status} /></td>
                    <td className="px-4 py-4">
                      <div className="flex justify-end gap-2">
                        {tab === "pending" && skill.status === "PENDING" ? (
                          <>
                            <Button type="button" size="sm" variant="ghost" disabled={busyId !== null} onClick={() => void review(skill, "reject")}>{busyId === skill.id ? "Đang xử lý..." : "Từ chối"}</Button>
                            <Button type="button" size="sm" variant="outline" disabled={busyId !== null} onClick={() => setMergeSource(skill)}>Hợp nhất</Button>
                            <Button type="button" size="sm" disabled={busyId !== null} onClick={() => void review(skill, "approve")}>{busyId === skill.id ? "Đang xử lý..." : "Duyệt"}</Button>
                          </>
                        ) : skill.status === "APPROVED" ? (
                          <Button type="button" size="sm" variant="outline" onClick={() => setSkillForm(skill)}>
                            {tab === "aliases" ? "Sửa bí danh" : "Chỉnh sửa"}
                          </Button>
                        ) : null}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="mt-5 rounded-xl border border-dashed border-zinc-300 px-5 py-12 text-center text-sm text-zinc-500">
            {tab === "pending" ? "Không có kỹ năng đang chờ duyệt." : "Chưa có kỹ năng phù hợp."}
          </div>
        )}

        {!loading && !state.error && state.result && (state.result.previous || state.result.next) && (
          <nav className="mt-5 flex flex-wrap items-center justify-center gap-3" aria-label="Phân trang kỹ năng">
            <Button type="button" variant="outline" size="sm" disabled={!state.result.previous} onClick={() => onQueryChange({ page: page - 1 })}>Trang trước</Button>
            <span className="text-sm font-medium text-zinc-600">Trang {page}</span>
            <Button type="button" variant="outline" size="sm" disabled={!state.result.next} onClick={() => onQueryChange({ page: page + 1 })}>Trang sau</Button>
          </nav>
        )}
      </div>

      {skillForm && (
        <SkillFormDialog
          key={skillForm === "new" ? "new" : skillForm.id}
          skill={skillForm === "new" ? null : skillForm}
          aliasesOnly={tab === "aliases"}
          onClose={() => setSkillForm(null)}
          onCreated={() => refresh("Kỹ năng đã được tạo; hãy hoàn tất danh sách bí danh.")}
          onSaved={(message) => { setSkillForm(null); refresh(message); }}
        />
      )}
      {categoryFormOpen && <CategoryFormDialog onClose={() => setCategoryFormOpen(false)} onSaved={() => { setCategoryFormOpen(false); setNotice("Đã thêm danh mục kỹ năng."); }} />}
      {mergeSource && <SkillMergeDialog source={mergeSource} onClose={() => setMergeSource(null)} onMerged={() => { setMergeSource(null); refresh("Đã hợp nhất kỹ năng.", true); }} />}
    </section>
  );
}

function AliasBadges({ skill, showAll }: { skill: AdminSkillDto; showAll: boolean }) {
  if (!skill.aliases.length) return <span className="text-xs text-zinc-400">Chưa có</span>;
  const visibleAliases = showAll ? skill.aliases : skill.aliases.slice(0, 3);
  return (
    <div className="flex flex-wrap gap-1.5">
      {visibleAliases.map((alias) => <Badge key={alias.id} variant="outline">{alias.alias_text}</Badge>)}
      {!showAll && skill.aliases.length > 3 && <Badge variant="outline">+{skill.aliases.length - 3}</Badge>}
    </div>
  );
}

function SkillStatusBadge({ status }: { status: AdminSkillDto["status"] }) {
  return <Badge variant="outline" className={STATUS_CLASSES[status]}>{STATUS_LABELS[status]}</Badge>;
}

function SkillsSkeleton() {
  return (
    <div className="mt-5 space-y-2" aria-label="Đang tải kỹ năng" aria-busy="true">
      {[0, 1, 2, 3, 4].map((item) => <div key={item} className="h-16 animate-pulse rounded-xl bg-zinc-100" />)}
    </div>
  );
}

function SkillFormDialog({
  skill,
  aliasesOnly,
  onClose,
  onCreated,
  onSaved,
}: {
  skill: AdminSkillDto | null;
  aliasesOnly: boolean;
  onClose: () => void;
  onCreated: () => void;
  onSaved: (message: string) => void;
}) {
  const [name, setName] = useState(skill?.name ?? "");
  const [category, setCategory] = useState(skill?.category ?? "");
  const [aliases, setAliases] = useState(skill?.aliases.map((alias) => alias.alias_text).join(", ") ?? "");
  const [isActive, setIsActive] = useState(skill?.is_active ?? true);
  const [categories, setCategories] = useState<SkillCategoryDto[]>([]);
  const [categoriesError, setCategoriesError] = useState<string | null>(null);
  const [nameError, setNameError] = useState<string | null>(null);
  const [aliasesError, setAliasesError] = useState<string | null>(null);
  const [serverError, setServerError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [createdSkill, setCreatedSkill] = useState<AdminSkillDto | null>(null);
  const effectiveSkill = skill ?? createdSkill;

  useEffect(() => {
    if (aliasesOnly) return;
    const controller = new AbortController();
    getSkillCategories(controller.signal)
      .then(setCategories)
      .catch((reason: unknown) => { if (!controller.signal.aborted) setCategoriesError(reason instanceof Error ? reason.message : "Không thể tải danh mục."); });
    return () => controller.abort();
  }, [aliasesOnly]);

  const submit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const trimmedName = name.trim();
    const aliasValues = aliases.split(",").map((value) => value.trim()).filter(Boolean);
    const normalizedAliases = aliasValues.map((value) => value.toLocaleLowerCase("vi-VN"));
    setNameError(aliasesOnly || trimmedName ? null : "Tên kỹ năng không được để trống.");
    setAliasesError(new Set(normalizedAliases).size === normalizedAliases.length ? null : "Bí danh không được trùng nhau.");
    if ((!aliasesOnly && !trimmedName) || new Set(normalizedAliases).size !== normalizedAliases.length) return;

    setSaving(true);
    setServerError(null);
    try {
      const payload: SkillCreatePayload | SkillUpdatePayload = aliasesOnly
        ? { aliases: aliasValues }
        : { name: trimmedName, category: category || null, aliases: aliasValues, is_active: isActive };
      if (effectiveSkill) {
        await updateAdminSkill(effectiveSkill.id, payload);
        onSaved(skill ? "Đã cập nhật kỹ năng." : "Đã hoàn tất kỹ năng mới.");
        return;
      }
      const created = await createAdminSkill({
        ...(payload as SkillCreatePayload),
        aliases: [],
      });
      onCreated();
      if (aliasValues.length > 0) {
        try {
          await updateAdminSkill(created.id, { aliases: aliasValues });
        } catch (reason) {
          const message = reason instanceof Error ? reason.message : "Không thể lưu bí danh.";
          setCreatedSkill(created);
          setAliasesError(`Kỹ năng đã được tạo nhưng chưa lưu được bí danh: ${message}`);
          return;
        }
      }
      onSaved("Đã thêm kỹ năng.");
    } catch (reason) {
      const message = reason instanceof Error ? reason.message : "Không thể lưu kỹ năng.";
      if (message.toLocaleLowerCase("vi-VN").includes("alias")) setAliasesError(message);
      else setServerError(message);
    } finally {
      setSaving(false);
    }
  };

  return (
    <Modal title={aliasesOnly ? `Sửa bí danh · ${skill?.name}` : effectiveSkill ? "Chỉnh sửa kỹ năng" : "Thêm kỹ năng"} description="Tên chuẩn và bí danh được dùng để đồng nhất dữ liệu hồ sơ và tin tuyển dụng." onClose={onClose} canClose={!saving}>
      <form onSubmit={submit} className="space-y-4">
        {!aliasesOnly && <><label className="block text-sm font-medium text-zinc-700">Tên kỹ năng *<Input value={name} onChange={(event) => setName(event.target.value)} className="mt-1.5" maxLength={150} aria-invalid={Boolean(nameError)} /></label>{nameError && <p className="text-xs text-red-600">{nameError}</p>}<label className="block text-sm font-medium text-zinc-700">Danh mục<select value={category} onChange={(event) => setCategory(event.target.value)} className="mt-1.5 h-11 w-full rounded-xl border border-zinc-300 bg-white px-3.5 text-sm">{!effectiveSkill?.category && <option value="">Không phân nhóm</option>}{categories.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select></label>{categoriesError && <p className="text-xs text-red-600">{categoriesError}</p>}</>}
        <label className="block text-sm font-medium text-zinc-700">Bí danh<Input value={aliases} onChange={(event) => setAliases(event.target.value)} className="mt-1.5" placeholder="ReactJS, React.js" aria-invalid={Boolean(aliasesError)} /></label>
        <p className="text-xs text-zinc-400">Phân tách nhiều bí danh bằng dấu phẩy.</p>
        {aliasesError && <p className="text-xs text-red-600">{aliasesError}</p>}
        {!aliasesOnly && <label className="flex items-center gap-2 text-sm text-zinc-700"><input type="checkbox" checked={isActive} onChange={(event) => setIsActive(event.target.checked)} className="size-4 accent-primary" />Đang hoạt động</label>}
        {serverError && <p className="rounded-lg bg-red-50 p-3 text-sm text-red-700" role="alert">{serverError}</p>}
        <div className="flex justify-end gap-2 pt-2"><Button type="button" variant="ghost" onClick={onClose} disabled={saving}>{createdSkill ? "Đóng" : "Hủy"}</Button><Button disabled={saving}>{saving ? "Đang lưu..." : "Lưu"}</Button></div>
      </form>
    </Modal>
  );
}

function CategoryFormDialog({ onClose, onSaved }: { onClose: () => void; onSaved: () => void }) {
  const [name, setName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const submit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const value = name.trim();
    if (!value) { setError("Tên danh mục không được để trống."); return; }
    setSaving(true);
    setError(null);
    try { await createSkillCategory({ name: value }); onSaved(); }
    catch (reason) { setError(reason instanceof Error ? reason.message : "Không thể thêm danh mục."); }
    finally { setSaving(false); }
  };
  return (
    <Modal title="Thêm danh mục kỹ năng" description="Tạo nhóm dùng để phân loại các kỹ năng chuẩn." onClose={onClose} canClose={!saving}>
      <form onSubmit={submit} className="space-y-4"><label className="block text-sm font-medium text-zinc-700">Tên danh mục *<Input value={name} onChange={(event) => setName(event.target.value)} className="mt-1.5" maxLength={150} /></label>{error && <p className="text-sm text-red-600" role="alert">{error}</p>}<div className="flex justify-end gap-2"><Button type="button" variant="ghost" onClick={onClose} disabled={saving}>Hủy</Button><Button disabled={saving}>{saving ? "Đang lưu..." : "Lưu"}</Button></div></form>
    </Modal>
  );
}

function SkillMergeDialog({ source, onClose, onMerged }: { source: AdminSkillDto; onClose: () => void; onMerged: () => void }) {
  const [targets, setTargets] = useState<AdminSkillDto[]>([]);
  const [targetId, setTargetId] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  useEffect(() => {
    const controller = new AbortController();
    const loadTargets = async () => {
      const all: AdminSkillDto[] = [];
      let page = 1;
      let response: Paginated<AdminSkillDto>;
      do {
        response = await getAdminSkills({ status: "APPROVED", page_size: 100, page }, controller.signal);
        all.push(...response.results);
        page += 1;
      } while (response.next);
      return all;
    };
    loadTargets()
      .then(setTargets)
      .catch((reason: unknown) => { if (!controller.signal.aborted) setError(reason instanceof Error ? reason.message : "Không thể tải kỹ năng đích."); });
    return () => controller.abort();
  }, []);
  const options = targets.filter((skill) => skill.is_active && skill.id !== source.id);
  const submit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!targetId || targetId === source.id) { setError("Hãy chọn một kỹ năng đích khác kỹ năng nguồn."); return; }
    if (!window.confirm(`Hợp nhất “${source.name}” vào kỹ năng đã chọn? Thao tác này không thể hoàn tác.`)) return;
    setSaving(true);
    setError(null);
    try { await mergeSkills({ source_ids: [source.id], target_id: targetId }); onMerged(); }
    catch (reason) { setError(reason instanceof Error ? reason.message : "Không thể hợp nhất kỹ năng."); }
    finally { setSaving(false); }
  };
  return (
    <Modal title="Hợp nhất kỹ năng" description={`Kỹ năng nguồn: ${source.name}`} onClose={onClose} canClose={!saving}>
      <form onSubmit={submit} className="space-y-4">
        <p className="rounded-xl border border-amber-200 bg-amber-50 p-3 text-sm text-amber-800">Mọi hồ sơ và tin tuyển dụng đang tham chiếu kỹ năng nguồn sẽ được chuyển sang kỹ năng đích.</p>
        <label className="block text-sm font-medium text-zinc-700">Kỹ năng đích *<select value={targetId} onChange={(event) => setTargetId(event.target.value)} className="mt-1.5 h-11 w-full rounded-xl border border-zinc-300 bg-white px-3.5 text-sm" required><option value="">Chọn kỹ năng đã duyệt</option>{options.map((skill) => <option key={skill.id} value={skill.id}>{skill.name}</option>)}</select></label>
        {error && <p className="text-sm text-red-600" role="alert">{error}</p>}
        <div className="flex justify-end gap-2"><Button type="button" variant="ghost" onClick={onClose} disabled={saving}>Hủy</Button><Button disabled={saving || !targetId}>{saving ? "Đang hợp nhất..." : "Xác nhận hợp nhất"}</Button></div>
      </form>
    </Modal>
  );
}

function Modal({ title, description, onClose, canClose, children }: { title: string; description: string; onClose: () => void; canClose: boolean; children: React.ReactNode }) {
  const dialogRef = useRef<HTMLDivElement>(null);
  const requestClose = useEffectEvent(() => { if (canClose) onClose(); });
  useEffect(() => {
    const previousFocus = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    const focusableSelector = "button:not([disabled]), input:not([disabled]), select:not([disabled]), [href], [tabindex]:not([tabindex='-1'])";
    const focusable = () => Array.from(dialogRef.current?.querySelectorAll<HTMLElement>(focusableSelector) ?? []);
    focusable()[0]?.focus();
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") requestClose();
      if (event.key !== "Tab") return;
      const items = focusable();
      if (!items.length) return;
      const first = items[0];
      const last = items[items.length - 1];
      if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); }
      else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => { window.removeEventListener("keydown", handleKeyDown); previousFocus?.focus(); };
  }, []);
  return (
    <div className="fixed inset-0 z-50 grid place-items-center overflow-y-auto bg-zinc-950/45 p-4" role="dialog" aria-modal="true" aria-labelledby="admin-dialog-title">
      <div ref={dialogRef} className="w-full max-w-lg rounded-2xl bg-white p-5 shadow-xl sm:p-6">
        <div className="mb-5"><h2 id="admin-dialog-title" className="text-lg font-bold text-zinc-900">{title}</h2><p className="mt-1 text-sm text-zinc-500">{description}</p></div>
        {children}
      </div>
    </div>
  );
}
