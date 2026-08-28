"use client";

import { Save, Sparkles, X } from "lucide-react";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { saveCandidateProfile } from "@/features/candidates/api";
import type {
  CandidateProfileDto,
  CandidateSkillDto,
  EducationDto,
  ExperienceDto,
  ProfileSavePayload,
  ProfileUpdatePayload,
  ResumeImportDto,
  ResumePreview,
} from "@/features/candidates/types";
import { BasicInfoSection } from "./basic-info-section";
import { EducationSection } from "./education-section";
import { ExperienceSection } from "./experience-section";
import { SkillsSection } from "./skills-section";

type DraftProfile = Omit<CandidateProfileDto, "gender"> & {
  gender: NonNullable<ProfileUpdatePayload["gender"]>;
};

function draftEducation(item: NonNullable<ResumePreview["educations"]>[number]): EducationDto {
  const now = new Date().toISOString();
  return {
    id: crypto.randomUUID(),
    school_name: item.school_name,
    major: item.major ?? "",
    degree: item.degree ?? "",
    start_date: item.start_date ?? null,
    end_date: item.end_date ?? null,
    description: item.description ?? "",
    source: "AI_EXTRACTED",
    created_at: now,
    updated_at: now,
  };
}

function draftExperience(item: NonNullable<ResumePreview["experiences"]>[number]): ExperienceDto {
  const now = new Date().toISOString();
  return {
    id: crypto.randomUUID(),
    company_name: item.company_name,
    position: item.position,
    start_date: item.start_date ?? null,
    end_date: item.end_date ?? null,
    is_current: item.is_current ?? false,
    description: item.description ?? "",
    source: "AI_EXTRACTED",
    created_at: now,
    updated_at: now,
  };
}

export function CandidateProfileEditor({
  profile,
  previewImport,
  onSaved,
  onCancel,
}: {
  profile: CandidateProfileDto;
  previewImport?: ResumeImportDto | null;
  onSaved: (profile: CandidateProfileDto) => void;
  onCancel?: () => void;
}) {
  const preview = previewImport?.parsed_data as ResumePreview | null;
  const previewLabel = previewImport?.original_filename;
  const [draftProfile, setDraftProfile] = useState<DraftProfile>({
    ...profile,
    full_name: preview?.full_name || profile.full_name,
    phone: preview?.phone || profile.phone,
    headline: preview?.headline || profile.headline,
    summary: preview?.summary || profile.summary,
  });
  const [educations, setEducations] = useState<EducationDto[]>(
    preview?.educations ? preview.educations.map(draftEducation) : profile.educations,
  );
  const [experiences, setExperiences] = useState<ExperienceDto[]>(
    preview?.experiences ? preview.experiences.map(draftExperience) : profile.experiences,
  );
  const [skills, setSkills] = useState<CandidateSkillDto[]>(profile.skills);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  const updateBasicInfo = async (payload: Partial<ProfileUpdatePayload>) => {
    setDraftProfile((current) => ({ ...current, ...payload }));
    setMessage("Thay đổi đang ở bản nháp. Chọn Xác nhận & Lưu để áp dụng.");
    return true;
  };

  const save = async () => {
    setPending(true);
    setError(null);
    setMessage(null);
    const payload: ProfileSavePayload = {
      full_name: draftProfile.full_name,
      phone: draftProfile.phone,
      dob: draftProfile.dob,
      gender: draftProfile.gender,
      address: draftProfile.address,
      avatar_url: draftProfile.avatar_url,
      headline: draftProfile.headline,
      summary: draftProfile.summary,
      desired_position: draftProfile.desired_position,
      desired_salary_min: draftProfile.desired_salary_min,
      is_public: draftProfile.is_public,
      educations: educations.map((item) => ({
        school_name: item.school_name,
        major: item.major,
        degree: item.degree,
        start_date: item.start_date,
        end_date: item.end_date,
        description: item.description,
      })),
      experiences: experiences.map((item) => ({
        company_name: item.company_name,
        position: item.position,
        start_date: item.start_date,
        end_date: item.end_date,
        is_current: item.is_current,
        description: item.description,
      })),
      skills: skills.map((item) => ({
        skill: item.skill,
        level: item.level ?? "",
        years_of_experience: item.years_of_experience,
      })),
      resume_import_id: previewImport?.id ?? null,
    };

    try {
      const saved = await saveCandidateProfile(payload);
      setDraftProfile(saved);
      setMessage("Hồ sơ đã được lưu. Hệ thống đang cập nhật AI matching.");
      onSaved(saved);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Không thể lưu hồ sơ.");
    } finally {
      setPending(false);
    }
  };

  return (
    <div className="space-y-6">
      {preview && (
        <div className="flex items-start gap-3 rounded-2xl border border-primary-200 bg-primary-50 p-4 text-sm text-primary-900">
          <Sparkles className="mt-0.5 size-5 shrink-0" />
          <div>
            <p className="font-semibold">Đang xem bản nháp trích xuất từ {previewLabel}</p>
            <p className="mt-1 text-primary-700">Kiểm tra và chỉnh sửa từng mục trước khi xác nhận lưu hồ sơ.</p>
          </div>
        </div>
      )}
      <BasicInfoSection
        profile={draftProfile as CandidateProfileDto}
        pending={pending}
        onSave={updateBasicInfo}
      />
      <EducationSection items={educations} pending={pending} onChange={setEducations} />
      <ExperienceSection items={experiences} pending={pending} onChange={setExperiences} />
      <SkillsSection
        items={skills}
        pending={pending}
        onChange={setSkills}
        previewSkillNames={preview?.skills}
      />
      {error && (
        <p className="rounded-xl border border-red-200 bg-red-50 p-3 text-sm text-red-700">{error}</p>
      )}
      {message && (
        <p className="rounded-xl border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-700">{message}</p>
      )}
      <div className="sticky bottom-4 z-10 flex justify-end gap-2 rounded-2xl border border-zinc-200 bg-white/95 p-4 shadow-lg backdrop-blur">
        {onCancel && (
          <Button type="button" size="lg" variant="outline" onClick={onCancel} disabled={pending}>
            <X />
            {preview ? "Hủy bản nháp" : "Hủy"}
          </Button>
        )}
        <Button type="button" size="lg" onClick={save} disabled={pending}>
          <Save />
          {pending ? "Đang lưu hồ sơ..." : "Xác nhận & Lưu hồ sơ"}
        </Button>
      </div>
    </div>
  );
}
