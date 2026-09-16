"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import { ApiError } from "@/lib/api-client";
import { useStatusPolling } from "@/lib/use-status-polling";

type ImportControllerOptions<T, S> = {
  enabled: boolean;
  storageKey: string | null;
  start: (file: File) => Promise<T>;
  poll: (id: string) => Promise<T>;
  cancel: (id: string) => Promise<void>;
  getStatus: (item: T) => S;
  isProcessing: (status: S) => boolean;
  rateLimitMessage: string;
};

export function useImportController<T extends { id: string; expires_at?: string | null }, S extends string>({
  enabled,
  storageKey,
  start,
  poll,
  cancel,
  getStatus,
  isProcessing,
  rateLimitMessage,
}: ImportControllerOptions<T, S>) {
  const [item, setItem] = useState<T | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [isCancelling, setIsCancelling] = useState(false);
  const [cancelError, setCancelError] = useState<string | null>(null);
  const mounted = useRef(false);
  useEffect(() => {
    mounted.current = true;
    return () => { mounted.current = false; };
  }, []);

  // Chỉ khôi phục ID; snapshot luôn được lấy lại từ backend.
  const [restoredId, setRestoredId] = useState<string | null>(() =>
    typeof window === "undefined" || !storageKey ? null : localStorage.getItem(storageKey),
  );
  const importId = item?.id ?? restoredId;

  const { stalled, pollError, retry, stop } = useStatusPolling<T, S>({
    enabled: enabled && !isCancelling && Boolean(importId) && (!item || isProcessing(getStatus(item))),
    importId,
    poll,
    getStatus,
    isProcessing,
    onUpdate: (snapshot) => {
      if (getStatus(snapshot) === "CONSUMED" || isExpired(snapshot)) {
        clearImport();
        return;
      }
      setRestoredId(null);
      setItem(snapshot);
    },
    onError: (error) => {
      if (isMissingImport(error)) clearImport();
    },
  });

  const clearImport = useCallback(() => {
    stop();
    if (storageKey) localStorage.removeItem(storageKey);
    setRestoredId(null);
    setItem(null);
    setCancelError(null);
  }, [storageKey, stop]);

  useEffect(() => {
    if (!item?.expires_at) return;
    const timer = window.setTimeout(clearImport, Math.max(0, Date.parse(item.expires_at) - Date.now()));
    return () => window.clearTimeout(timer);
  }, [item?.expires_at, clearImport]);

  const cancelImport = async (): Promise<boolean> => {
    if (isCancelling) return false;
    stop();
    setIsCancelling(true);
    setCancelError(null);
    try {
      if (importId) await cancel(importId);
      clearImport();
      return true;
    } catch (error) {
      if (isMissingImport(error) || (item && isExpired(item))) {
        clearImport();
        return true;
      }
      setCancelError(error instanceof Error ? error.message : "Không thể xóa kết quả. Vui lòng thử lại.");
      retry();
      return false;
    } finally {
      setIsCancelling(false);
    }
  };

  const startImport = async (file: File) => {
    if (!enabled || !storageKey || isUploading || isCancelling) {
      throw new Error("Chưa thể tải tài liệu lúc này. Vui lòng thử lại.");
    }
    setIsUploading(true);
    try {
      if (importId && !(await cancelImport())) {
        throw new Error("Chưa thể xóa bản trích xuất cũ. Vui lòng thử lại.");
      }
      if (!mounted.current) throw new Error("Phiên làm việc đã thay đổi.");
      const result = await start(file);
      localStorage.setItem(storageKey, result.id);
      if (!mounted.current) throw new Error("Phiên làm việc đã thay đổi.");
      setRestoredId(null);
      setItem(result);
      return result;
    } catch (error) {
      if (error instanceof ApiError && error.status === 429) {
        throw new Error(rateLimitMessage);
      }
      throw error;
    } finally {
      setIsUploading(false);
    }
  };

  return {
    item, hasImport: Boolean(importId), isUploading, isCancelling, cancelError,
    stalled, pollError, retry, startImport, cancelImport, clearImport,
  };
}

function isExpired(item: { expires_at?: string | null }) {
  return Boolean(item.expires_at && Date.parse(item.expires_at) <= Date.now());
}

function isMissingImport(error: unknown) {
  return error instanceof ApiError && (error.status === 404 || error.status === 410);
}
