"use client";

import { createContext, useContext, useEffect, useState } from "react";

import { cancelJDImport, getJDImport, parseJobDescription } from "@/features/employer/api";
import type { JDImportDto } from "@/features/employer/types";
import { useAuth } from "@/lib/auth-provider";

const STORAGE_KEY = "active-jd-import";

type JDImportContextValue = {
  jdImport: JDImportDto | null;
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

  useEffect(() => {
    if (!jdImport || !["PENDING", "PROCESSING"].includes(jdImport.status)) return;
    const timer = window.setInterval(() => {
      void getJDImport(jdImport.id).then((result) => {
        if (result.status === "CONSUMED") clearImport();
        else setJDImport(result);
      }).catch(clearImport);
    }, 2000);
    return () => window.clearInterval(timer);
  }, [jdImport]);

  const startImport = async (file: File) => {
    const result = await parseJobDescription(file);
    localStorage.setItem(STORAGE_KEY, result.id);
    setJDImport(result);
    return result;
  };

  const cancelImport = async () => {
    if (jdImport) await cancelJDImport(jdImport.id);
    clearImport();
  };

  return (
    <JDImportContext.Provider value={{ jdImport, startImport, cancelImport, clearImport }}>
      {children}
    </JDImportContext.Provider>
  );
}

export function useJDImport() {
  const context = useContext(JDImportContext);
  if (!context) throw new Error("useJDImport must be used within JDImportProvider");
  return context;
}
