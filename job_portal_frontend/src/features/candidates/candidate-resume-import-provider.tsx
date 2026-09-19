"use client";

import { createContext, useContext } from "react";

import { cancelResumeImport, getResumeImport, parseResumeImport } from "@/features/candidates/api";
import type { ResumeImportDto } from "@/features/candidates/types";
import { useAuth } from "@/lib/auth-provider";
import { useImportController } from "@/lib/use-import-controller";

type CandidateResumeImportContextValue = {
  resumeImport: ResumeImportDto | null;
  hasImport: boolean;
  isUploading: boolean;
  isCancelling: boolean;
  cancelError: string | null;
  stalled: boolean;
  pollError: boolean;
  retry: () => void;
  startImport: (file: File) => Promise<ResumeImportDto>;
  cancelImport: () => Promise<boolean>;
  clearImport: () => void;
};

const CandidateResumeImportContext = createContext<CandidateResumeImportContextValue | null>(null);

export function CandidateResumeImportProvider({ children }: { children: React.ReactNode }) {
  const { user } = useAuth();
  const userId = user?.role === "CANDIDATE" ? user.id : null;
  // Đổi tài khoản thì bỏ state trong bộ nhớ, giữ key cũ để chủ tài khoản quay lại.
  return <ResumeImportSession key={userId ?? "anonymous"} userId={userId}>{children}</ResumeImportSession>;
}

function ResumeImportSession({ userId, children }: { userId: string | null; children: React.ReactNode }) {
  const { item: resumeImport, ...controller } = useImportController({
    enabled: Boolean(userId),
    storageKey: userId ? `resume_import_id:${userId}` : null,
    start: parseResumeImport,
    poll: getResumeImport,
    cancel: cancelResumeImport,
    getStatus: (snapshot) => snapshot.parse_status,
    isProcessing: (status) => status === "PENDING" || status === "PROCESSING",
    rateLimitMessage:
      "Bạn đã tải CV quá nhiều lần (tối đa 2 lượt/phút, 10 lượt/ngày). Vui lòng thử lại sau.",
  });

  return (
    <CandidateResumeImportContext.Provider value={{ resumeImport, ...controller }}>
      {children}
    </CandidateResumeImportContext.Provider>
  );
}

export function useCandidateResumeImport() {
  const context = useContext(CandidateResumeImportContext);
  if (!context) {
    throw new Error("useCandidateResumeImport must be used within CandidateResumeImportProvider");
  }
  return context;
}
