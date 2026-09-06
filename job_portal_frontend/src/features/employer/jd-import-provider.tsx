"use client";

import { createContext, useCallback, useContext, useState } from "react";

import { cancelJDImport, getJDImport, parseJobDescription } from "@/features/employer/api";
import type { JDImportDto } from "@/features/employer/types";
import { ApiError } from "@/lib/api-client";
import { useAuth } from "@/lib/auth-provider";
import { useStatusPolling } from "@/lib/use-status-polling";

const STORAGE_KEY = "active-jd-import";

type JDParseStatus = JDImportDto["status"];

type JDImportContextValue = {
  jdImport: JDImportDto | null;
  /** Poll đã tự ngắt sau 2 phút mà JD vẫn chưa xong. */
  stalled: boolean;
  /** Request gần nhất gặp lỗi mạng / khôi phục; import ID vẫn giữ trong localStorage. */
  pollError: boolean;
  /** Gọi GET ngay và tiếp tục polling nếu tác vụ vẫn hoạt động. */
  retry: () => void;
  startImport: (file: File) => Promise<JDImportDto>;
  cancelImport: () => Promise<void>;
  clearImport: () => void;
};

const JDImportContext = createContext<JDImportContextValue | null>(null);

export function JDImportProvider({ children }: { children: React.ReactNode }) {
  const { user } = useAuth();
  const [jdImport, setJDImport] = useState<JDImportDto | null>(null);
  const [restoredId, setRestoredId] = useState<string | null>(() =>
    typeof window === "undefined" ? null : localStorage.getItem(STORAGE_KEY),
  );

  const isProcessingJD = useCallback(
    (status: JDParseStatus) => status === "PENDING" || status === "PROCESSING",
    [],
  );

  const handleJDUpdate = useCallback((snapshot: JDImportDto) => {
    setRestoredId(null);
    if (snapshot.status === "CONSUMED") {
      localStorage.removeItem(STORAGE_KEY);
      setJDImport(null);
      return;
    }
    setJDImport(snapshot);
  }, []);

  const handleJDError = useCallback((error: unknown) => {
    if (error instanceof ApiError && error.status === 404) {
      localStorage.removeItem(STORAGE_KEY);
      setRestoredId(null);
      setJDImport(null);
    }
  }, []);

  const importId = jdImport?.id ?? restoredId;

  const { stalled, pollError: hookPollError, retry: retryPolling } = useStatusPolling<
    JDImportDto,
    JDParseStatus
  >({
    enabled: user?.role === "EMPLOYER" && Boolean(importId) && (!jdImport || isProcessingJD(jdImport.status)),
    importId,
    poll: getJDImport,
    getStatus: (snapshot) => snapshot.status,
    isProcessing: isProcessingJD,
    onUpdate: handleJDUpdate,
    onError: handleJDError,
  });

  const retry = useCallback(() => {
    retryPolling();
  }, [retryPolling]);

  const startImport = async (file: File) => {
    try {
      const result = await parseJobDescription(file);
      localStorage.setItem(STORAGE_KEY, result.id);
      setRestoredId(null);
      setJDImport(result);
      return result;
    } catch (error) {
      if (error instanceof ApiError && error.status === 429) {
        throw new Error(
          "Bạn đã tải JD quá nhiều lần (tối đa 2 lượt/phút, 10 lượt/ngày). Vui lòng thử lại sau.",
        );
      }
      throw error;
    }
  };

  const cancelImport = async () => {
    if (importId) await cancelJDImport(importId);
    localStorage.removeItem(STORAGE_KEY);
    setRestoredId(null);
    setJDImport(null);
  };

  const clearImport = useCallback(() => {
    localStorage.removeItem(STORAGE_KEY);
    setRestoredId(null);
    setJDImport(null);
  }, []);

  return (
    <JDImportContext.Provider
      value={{
        jdImport,
        stalled,
        pollError: hookPollError,
        retry,
        startImport,
        cancelImport,
        clearImport,
      }}
    >
      {children}
    </JDImportContext.Provider>
  );
}

export function useJDImport() {
  const context = useContext(JDImportContext);
  if (!context) throw new Error("useJDImport must be used within JDImportProvider");
  return context;
}
