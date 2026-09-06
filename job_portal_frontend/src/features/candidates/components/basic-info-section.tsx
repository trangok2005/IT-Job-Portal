"use client";

import { Eye, EyeOff, Pencil, UserRound } from "lucide-react";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import type {
  CandidateProfileDto,
  ProfileUpdatePayload,
} from "@/features/candidates/types";
import {
  FieldLabel,
  ProfileSection,
  fieldClassName,
  textareaClassName,
} from "@/features/candidates/components/profile-section";

const genderLabels = { MALE: "Nam", FEMALE: "Nữ", OTHER: "Khác", "": "Chưa cập nhật" };

function display(value: string | number | null | undefined) {
  return value === null || value === undefined || value === "" ? "Chưa cập nhật" : String(value);
}

export function BasicInfoSection({
  profile,
  pending,
  onSave,
}: {
  profile: CandidateProfileDto;
  pending: boolean;
  onSave: (payload: Partial<ProfileUpdatePayload>) => Promise<boolean>;
}) {
  const [editing, setEditing] = useState(false);

  const submit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const saved = await onSave({
      full_name: String(form.get("full_name") ?? "").trim(),
      phone: String(form.get("phone") ?? "").trim(),
      dob: String(form.get("dob") ?? "") || null,
      gender: String(form.get("gender") ?? "") as ProfileUpdatePayload["gender"],
      address: String(form.get("address") ?? "").trim(),
      avatar_url: String(form.get("avatar_url") ?? "").trim(),
      headline: String(form.get("headline") ?? "").trim(),
      summary: String(form.get("summary") ?? "").trim(),
      desired_position: String(form.get("desired_position") ?? "").trim(),
      is_public: form.get("is_public") === "on",
    });
    if (saved) setEditing(false);
  };

  return (
    <ProfileSection
      id="basic-info"
      icon={UserRound}
      title="Thông tin cá nhân"
      description="Thông tin liên hệ và định hướng nghề nghiệp của bạn."
      action={
        !editing ? (
          <Button type="button" variant="ghost" size="sm" onClick={() => setEditing(true)}>
            <Pencil />
            <span className="hidden sm:inline">Chỉnh sửa</span>
          </Button>
        ) : undefined
      }
    >
      {!editing ? (
        <div className="space-y-6">
          <div>
            <p className="text-lg font-semibold text-zinc-900">{display(profile.headline)}</p>
            <p className="mt-2 whitespace-pre-line text-sm leading-6 text-zinc-600">
              {display(profile.summary)}
            </p>
          </div>
          <dl className="grid gap-x-8 gap-y-5 border-t border-zinc-100 pt-5 sm:grid-cols-2">
            {[
              ["Họ và tên", profile.full_name],
              ["Email", profile.email],
              ["Số điện thoại", profile.phone],
              ["Ngày sinh", profile.dob],
              ["Giới tính", genderLabels[profile.gender]],
              ["Địa chỉ", profile.address],
              ["Vị trí mong muốn", profile.desired_position],
            ].map(([label, value]) => (
              <div key={label}>
                <dt className="text-xs font-medium uppercase tracking-wide text-zinc-400">{label}</dt>
                <dd className="mt-1 text-sm font-medium text-zinc-800">{display(value)}</dd>
              </div>
            ))}
          </dl>
          <div className="flex items-center gap-2 rounded-xl bg-primary-50 px-3.5 py-3 text-sm text-primary-800">
            {profile.is_public ? <Eye className="size-4" /> : <EyeOff className="size-4" />}
            {profile.is_public
              ? "Nhà tuyển dụng có thể tìm thấy hồ sơ của bạn."
              : "Hồ sơ đang ẩn khỏi kết quả tìm kiếm của nhà tuyển dụng."}
          </div>
        </div>
      ) : (
        <form onSubmit={submit} className="space-y-5">
          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <FieldLabel htmlFor="full_name">Họ và tên *</FieldLabel>
              <Input id="full_name" name="full_name" defaultValue={profile.full_name} required />
            </div>
            <div>
              <FieldLabel htmlFor="phone">Số điện thoại *</FieldLabel>
              <Input id="phone" name="phone" defaultValue={profile.phone} required />
            </div>
            <div>
              <FieldLabel htmlFor="dob">Ngày sinh</FieldLabel>
              <Input id="dob" name="dob" type="date" defaultValue={profile.dob ?? ""} />
            </div>
            <div>
              <FieldLabel htmlFor="gender">Giới tính</FieldLabel>
              <select id="gender" name="gender" defaultValue={profile.gender} className={fieldClassName}>
                <option value="">Chọn giới tính</option>
                <option value="MALE">Nam</option>
                <option value="FEMALE">Nữ</option>
                <option value="OTHER">Khác</option>
              </select>
            </div>
          </div>
          <div>
            <FieldLabel htmlFor="headline">Tiêu đề nghề nghiệp</FieldLabel>
            <Input
              id="headline"
              name="headline"
              defaultValue={profile.headline}
              placeholder="Ví dụ: Backend Developer · 3 năm kinh nghiệm"
            />
          </div>
          <div>
            <FieldLabel htmlFor="summary">Giới thiệu bản thân</FieldLabel>
            <textarea
              id="summary"
              name="summary"
              defaultValue={profile.summary}
              className={textareaClassName}
              placeholder="Tóm tắt kinh nghiệm, thế mạnh và mục tiêu nghề nghiệp..."
            />
          </div>
          <div>
            <FieldLabel htmlFor="desired_position">Vị trí mong muốn *</FieldLabel>
            <Input
              id="desired_position"
              name="desired_position"
              defaultValue={profile.desired_position}
              required
            />
          </div>
          <div>
            <FieldLabel htmlFor="address">Địa chỉ</FieldLabel>
            <Input id="address" name="address" defaultValue={profile.address} />
          </div>
          <div>
            <FieldLabel htmlFor="avatar_url">URL ảnh đại diện</FieldLabel>
            <Input id="avatar_url" name="avatar_url" type="url" defaultValue={profile.avatar_url} />
          </div>
          <label className="flex cursor-pointer items-start gap-3 rounded-xl border border-zinc-200 p-3.5">
            <input
              name="is_public"
              type="checkbox"
              defaultChecked={profile.is_public}
              className="mt-0.5 size-4 accent-primary"
            />
            <span>
              <span className="block text-sm font-medium text-zinc-800">Cho phép tìm kiếm hồ sơ</span>
              <span className="mt-0.5 block text-xs text-zinc-500">
                Nhà tuyển dụng có thể thấy hồ sơ khi tìm ứng viên phù hợp.
              </span>
            </span>
          </label>
          <div className="flex flex-col-reverse gap-2 border-t border-zinc-100 pt-5 sm:flex-row sm:justify-end">
            <Button type="button" variant="ghost" onClick={() => setEditing(false)} disabled={pending}>
              Hủy
            </Button>
            <Button type="submit" disabled={pending}>
              {pending ? "Đang lưu..." : "Lưu thông tin"}
            </Button>
          </div>
        </form>
      )}
    </ProfileSection>
  );
}
