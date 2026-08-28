"use client";

import { createContext, useCallback, useContext, useEffect, useState } from "react";

import {
  cancelResumeImport,
  getResumeImport,
  parseResumeImport,
} from "@/features/candidates/api";
import type { ResumeImportDto } from "@/features/candidates/types";
import { ApiError } from "@/lib/api-client";
import { useAuth } from "@/lib/auth-provider";
import { useStatusPolling } from "@/lib/use-status-polling";

const STORAGE_KEY = "active-resume-import";

type CandidateResumeImportContextValue = {
  resumeImport: ResumeImportDto | null;
  /** Poll đã tự ngắt sau 2 phút mà CV vẫn chưa xong → mời tải lại trang. */
  stalled: boolean;
  startImport: (file: File) => Promise<ResumeImportDto>;
  cancelImport: () => Promise<void>;
  clearImport: () => void;
};

const CandidateResumeImportContext = createContext<
  CandidateResumeImportContextValue | null
>(null);

export function CandidateResumeImportProvider({ children }: {
  children: React.ReactNode;
}) {
  const { user } = useAuth();
  const [resumeImport, setResumeImport] = useState<ResumeImportDto | null>(null);

  const clearImport = () => {
    localStorage.removeItem(STORAGE_KEY);
    setResumeImport(null);
  };

  useEffect(() => {
    if (user?.role !== "CANDIDATE") return;
    const id = localStorage.getItem(STORAGE_KEY);
    if (!id) return;
    void getResumeImport(id).then((result) => {
      if (result.parse_status === "CONSUMED") clearImport();
      else setResumeImport(result);
    }).catch(clearImport);
  }, [user?.role]);

  const isPending = resumeImport?.parse_status === "PENDING";

  const pollOnce = useCallback(async () => {
    if (!resumeImport) return;
    const result = await getResumeImport(resumeImport.id);
    if (result.parse_status === "CONSUMED") clearImport();
    else setResumeImport(result);
  }, [resumeImport]);

  const { stalled } = useStatusPolling({
    enabled: Boolean(isPending && resumeImport),
    poll: pollOnce,
    onError: clearImport,
  });

  const startImport = async (file: File) => {
    try {
      const result = await parseResumeImport(file);
      localStorage.setItem(STORAGE_KEY, result.id);
      setResumeImport(result);
      return result;
    } catch (error) {
      if (error instanceof ApiError && error.status === 429) {
        throw new Error(
          "Bạn đã tải CV quá nhiều lần (tối đa 2 lượt/phút, 10 lượt/ngày). Vui lòng thử lại sau.",
        );
      }
      throw error;
    }
  };

  const cancelImport = async () => {
    if (resumeImport) await cancelResumeImport(resumeImport.id);
    clearImport();
  };

  return (
    <CandidateResumeImportContext.Provider value={{ resumeImport, stalled, startImport, cancelImport, clearImport }}>
      {children}
    </CandidateResumeImportContext.Provider>
  );
}

const NOOP_VALUE: CandidateResumeImportContextValue = {
  resumeImport: null,
  stalled: false,
  startImport: async () => {
    throw new Error("CandidateResumeImportProvider is not mounted");
  },
  cancelImport: async () => {},
  clearImport: () => {},
};

// Navbar dùng hook này ở mọi trang (kể cả ngoài provider) nên phải trả về
// giá trị an toàn thay vì throw.
export function useCandidateResumeImport() {
  return useContext(CandidateResumeImportContext) ?? NOOP_VALUE;
}