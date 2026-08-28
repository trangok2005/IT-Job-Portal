"use client";

import { createContext, useCallback, useContext, useEffect, useState } from "react";

import { cancelJDImport, getJDImport, parseJobDescription } from "@/features/employer/api";
import type { JDImportDto } from "@/features/employer/types";
import { ApiError } from "@/lib/api-client";
import { useAuth } from "@/lib/auth-provider";
import { useStatusPolling } from "@/lib/use-status-polling";

const STORAGE_KEY = "active-jd-import";

type JDImportContextValue = {
  jdImport: JDImportDto | null;
  /** Poll đã tự ngắt sau 2 phút mà JD vẫn chưa xong → mời tải lại trang. */
  stalled: boolean;
  startImport: (file: File) => Promise<JDImportDto>;
  cancelImport: () => Promise<void>;
  clearImport: () => void;
};

const JDImportContext = createContext<JDImportContextValue | null>(null);

export function JDImportProvider({ children }: { children: React.ReactNode }) {
  const { user } = useAuth();
  const [jdImport, setJDImport] = useState<JDImportDto | null>(null);

  const clearImport = () => {
    localStorage.removeItem(STORAGE_KEY);
    setJDImport(null);
  };

  useEffect(() => {
    if (user?.role !== "EMPLOYER") return;
    const id = localStorage.getItem(STORAGE_KEY);
    if (!id) return;
    void getJDImport(id).then((result) => {
      if (result.status === "CONSUMED") clearImport();
      else setJDImport(result);
    }).catch(clearImport);
  }, [user?.role]);

  const isProcessing = jdImport !== null && ["PENDING", "PROCESSING"].includes(jdImport.status);

  const pollOnce = useCallback(async () => {
    if (!jdImport) return;
    const result = await getJDImport(jdImport.id);
    if (result.status === "CONSUMED") clearImport();
    else setJDImport(result);
  }, [jdImport]);

  const { stalled } = useStatusPolling({
    enabled: isProcessing,
    poll: pollOnce,
    onError: clearImport,
  });

  const startImport = async (file: File) => {
    try {
      const result = await parseJobDescription(file);
      localStorage.setItem(STORAGE_KEY, result.id);
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
    if (jdImport) await cancelJDImport(jdImport.id);
    clearImport();
  };

  return (
    <JDImportContext.Provider value={{ jdImport, stalled, startImport, cancelImport, clearImport }}>
      {children}
    </JDImportContext.Provider>
  );
}

export function useJDImport() {
  const context = useContext(JDImportContext);
  if (!context) throw new Error("useJDImport must be used within JDImportProvider");
  return context;
}
