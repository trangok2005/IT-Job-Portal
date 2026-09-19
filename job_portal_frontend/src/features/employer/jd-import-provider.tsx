"use client";

import { createContext, useContext } from "react";

import { cancelJDImport, getJDImport, parseJobDescription } from "@/features/employer/api";
import type { JDImportDto } from "@/features/employer/types";
import { useAuth } from "@/lib/auth-provider";
import { useImportController } from "@/lib/use-import-controller";

type JDImportContextValue = {
  jdImport: JDImportDto | null;
  hasImport: boolean;
  isUploading: boolean;
  isCancelling: boolean;
  cancelError: string | null;
  stalled: boolean;
  pollError: boolean;
  retry: () => void;
  startImport: (file: File) => Promise<JDImportDto>;
  cancelImport: () => Promise<boolean>;
  clearImport: () => void;
};

const JDImportContext = createContext<JDImportContextValue | null>(null);

export function JDImportProvider({ children }: { children: React.ReactNode }) {
  const { user } = useAuth();
  const userId = user?.role === "EMPLOYER" ? user.id : null;
  return <JDImportSession key={userId ?? "anonymous"} userId={userId}>{children}</JDImportSession>;
}

function JDImportSession({ userId, children }: { userId: string | null; children: React.ReactNode }) {
  const { item: jdImport, ...controller } = useImportController({
    enabled: Boolean(userId),
    storageKey: userId ? `jd_import_id:${userId}` : null,
    start: parseJobDescription,
    poll: getJDImport,
    cancel: cancelJDImport,
    getStatus: (snapshot) => snapshot.status,
    isProcessing: (status) => status === "PENDING" || status === "PROCESSING",
    rateLimitMessage:
      "Bạn đã tải JD quá nhiều lần (tối đa 2 lượt/phút, 10 lượt/ngày). Vui lòng thử lại sau.",
  });

  return (
    <JDImportContext.Provider value={{ jdImport, ...controller }}>
      {children}
    </JDImportContext.Provider>
  );
}

export function useJDImport() {
  const context = useContext(JDImportContext);
  if (!context) throw new Error("useJDImport must be used within JDImportProvider");
  return context;
}
