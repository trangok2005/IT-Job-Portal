"use client";

import { createContext, useCallback, useContext, useState } from "react";

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

type CVParseStatus = ResumeImportDto["parse_status"];

type CandidateResumeImportContextValue = {
  resumeImport: ResumeImportDto | null;
  /** Polling dừng sau 2 phút xử lý. */
  stalled: boolean;
  /** Polling lỗi nhưng import ID vẫn được giữ. */
  pollError: boolean;
  retry: () => void;
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
  const [restoredId, setRestoredId] = useState<string | null>(() =>
    typeof window === "undefined" ? null : localStorage.getItem(STORAGE_KEY),
  );

  const isProcessingCV = useCallback(
    (status: CVParseStatus) => status === "PENDING" || status === "PROCESSING",
    [],
  );

  const handleCVUpdate = useCallback((snapshot: ResumeImportDto) => {
    setRestoredId(null);
    if (snapshot.parse_status === "CONSUMED") {
      localStorage.removeItem(STORAGE_KEY);
      setResumeImport(null);
      return;
    }
    setResumeImport(snapshot);
  }, []);

  const handleCVError = useCallback((error: unknown) => {
    if (error instanceof ApiError && error.status === 404) {
      localStorage.removeItem(STORAGE_KEY);
      setRestoredId(null);
      setResumeImport(null);
    }
  }, []);

  const importId = resumeImport?.id ?? restoredId;

  const { stalled, pollError: hookPollError, retry: retryPolling } = useStatusPolling<
    ResumeImportDto,
    CVParseStatus
  >({
    enabled: user?.role === "CANDIDATE" && Boolean(importId) && (!resumeImport || isProcessingCV(resumeImport.parse_status)),
    importId,
    poll: getResumeImport,
    getStatus: (snapshot) => snapshot.parse_status,
    isProcessing: isProcessingCV,
    onUpdate: handleCVUpdate,
    onError: handleCVError,
  });

  const retry = useCallback(() => {
    retryPolling();
  }, [retryPolling]);

  const startImport = async (file: File) => {
    try {
      const result = await parseResumeImport(file);
      localStorage.setItem(STORAGE_KEY, result.id);
      setRestoredId(null);
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
    if (importId) await cancelResumeImport(importId);
    localStorage.removeItem(STORAGE_KEY);
    setRestoredId(null);
    setResumeImport(null);
  };

  const clearImport = useCallback(() => {
    localStorage.removeItem(STORAGE_KEY);
    setRestoredId(null);
    setResumeImport(null);
  }, []);

  return (
    <CandidateResumeImportContext.Provider
      value={{
        resumeImport,
        stalled,
        pollError: hookPollError,
        retry,
        startImport,
        cancelImport,
        clearImport,
      }}
    >
      {children}
    </CandidateResumeImportContext.Provider>
  );
}

const NOOP_VALUE: CandidateResumeImportContextValue = {
  resumeImport: null,
  stalled: false,
  pollError: false,
  retry: () => {},
  startImport: async () => {
    throw new Error("CandidateResumeImportProvider is not mounted");
  },
  cancelImport: async () => {},
  clearImport: () => {},
};

// Navbar gọi hook cả ngoài provider nên cần giá trị mặc định.
export function useCandidateResumeImport() {
  return useContext(CandidateResumeImportContext) ?? NOOP_VALUE;
}
