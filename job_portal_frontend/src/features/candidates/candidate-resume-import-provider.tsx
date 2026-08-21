"use client";

import { createContext, useContext, useEffect, useState } from "react";

import {
  cancelResumeImport,
  getResumeImport,
  parseResumeImport,
} from "@/features/candidates/api";
import type { ResumeImportDto } from "@/features/candidates/types";
import { useAuth } from "@/lib/auth-provider";

const STORAGE_KEY = "active-resume-import";

type CandidateResumeImportContextValue = {
  resumeImport: ResumeImportDto | null;
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

  useEffect(() => {
    // ResumeImport chỉ có PENDING là trạng thái "đang chạy" (UC-01 bước 10).
    if (!resumeImport || resumeImport.parse_status !== "PENDING") return;
    const timer = window.setInterval(() => {
      void getResumeImport(resumeImport.id).then((result) => {
        if (result.parse_status === "CONSUMED") clearImport();
        else setResumeImport(result);
      }).catch(clearImport);
    }, 2000);
    return () => window.clearInterval(timer);
  }, [resumeImport]);

  const startImport = async (file: File) => {
    const result = await parseResumeImport(file);
    localStorage.setItem(STORAGE_KEY, result.id);
    setResumeImport(result);
    return result;
  };

  const cancelImport = async () => {
    if (resumeImport) await cancelResumeImport(resumeImport.id);
    clearImport();
  };

  return (
    <CandidateResumeImportContext.Provider value={{ resumeImport, startImport, cancelImport, clearImport }}>
      {children}
    </CandidateResumeImportContext.Provider>
  );
}

const NOOP_VALUE: CandidateResumeImportContextValue = {
  resumeImport: null,
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