"use client";

import { useEffect, useEffectEvent, useState } from "react";

import { getCandidateProfile } from "@/features/candidates/api";
import type { CandidateProfileDto } from "@/features/candidates/types";

export function useCandidateProfile() {
  const [profile, setProfile] = useState<CandidateProfileDto | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const syncPending = Boolean(
    profile?.embedding_is_stale
      || profile?.resumes.some((resume) => resume.parse_status === "PENDING"),
  );

  const pollProfile = useEffectEvent(async () => {
    try {
      setProfile(await getCandidateProfile());
    } catch {
      // Giữ dữ liệu hiện tại; request tương tác tiếp theo sẽ hiển thị lỗi nếu cần.
    }
  });

  const refresh = async () => {
    setError(null);
    try {
      const nextProfile = await getCandidateProfile();
      setProfile(nextProfile);
      return nextProfile;
    } catch (err) {
      setError(err instanceof Error ? err.message : "Không thể tải hồ sơ.");
      throw err;
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    let active = true;
    getCandidateProfile()
      .then((nextProfile) => {
        if (active) setProfile(nextProfile);
      })
      .catch((err: unknown) => {
        if (active) {
          setError(err instanceof Error ? err.message : "Không thể tải hồ sơ.");
        }
      })
      .finally(() => {
        if (active) setIsLoading(false);
      });
    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    if (!syncPending) return;
    const interval = window.setInterval(() => void pollProfile(), 3000);
    return () => window.clearInterval(interval);
  }, [syncPending]);

  return { profile, setProfile, isLoading, error, setError, refresh };
}
