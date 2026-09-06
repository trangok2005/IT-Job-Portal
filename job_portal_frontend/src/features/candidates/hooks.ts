"use client";

import { useEffect, useState } from "react";

import { getCandidateProfile } from "@/features/candidates/api";
import type { CandidateProfileDto } from "@/features/candidates/types";

export function useCandidateProfile() {
  const [profile, setProfile] = useState<CandidateProfileDto | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

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

  return { profile, setProfile, isLoading, error, setError, refresh };
}
