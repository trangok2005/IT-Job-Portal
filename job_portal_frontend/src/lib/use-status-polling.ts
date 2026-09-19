"use client";

import { startTransition, useCallback, useEffect, useRef, useState } from "react";

const POLL_INTERVAL_MS = 2000;
// 60 lượt chờ × 2 giây, không tính lượt kiểm tra ngay khi mở/quay lại tab.
const MAX_POLL_COUNT = 60;

type StatusPollingOptions<T, S> = {
  enabled: boolean;
  importId: string | null;
  poll: (importId: string) => Promise<T>;
  getStatus: (snapshot: T) => S;
  isProcessing: (status: S) => boolean;
  onUpdate: (snapshot: T) => void;
  onError: (error: unknown) => void;
};

type PollUiState = {
  importId: string | null;
  stalled: boolean;
  pollError: boolean;
};

export function useStatusPolling<T, S>({
  enabled,
  importId,
  poll,
  getStatus,
  isProcessing,
  onUpdate,
  onError,
}: StatusPollingOptions<T, S>) {
  const [retryKey, setRetryKey] = useState(0);
  const [uiState, setUiState] = useState<PollUiState>({
    importId: null,
    stalled: false,
    pollError: false,
  });
  const pollCountRef = useRef(0);
  const inFlight = useRef(false);
  const stopRef = useRef<() => void>(() => {});

  const pollRef = useRef(poll);
  const getStatusRef = useRef(getStatus);
  const isProcessingRef = useRef(isProcessing);
  const onUpdateRef = useRef(onUpdate);
  const onErrorRef = useRef(onError);

  useEffect(() => {
    pollRef.current = poll;
    getStatusRef.current = getStatus;
    isProcessingRef.current = isProcessing;
    onUpdateRef.current = onUpdate;
    onErrorRef.current = onError;
  });

  useEffect(() => {
    pollCountRef.current = 0;
    startTransition(() => {
      setUiState({ importId, stalled: false, pollError: false });
    });
  }, [importId]);

  useEffect(() => {
    if (!enabled || !importId) return;
    let active = true;
    let pendingTimer: number | undefined;
    let pausedOnError = false;
    let stopped = false;

    const stopTimer = () => {
      if (pendingTimer !== undefined) {
        window.clearTimeout(pendingTimer);
        pendingTimer = undefined;
      }
    };

    const cancel = () => !active || !enabled;

    const stopPolling = () => {
      active = false;
      stopTimer();
      document.removeEventListener("visibilitychange", handleVisibility);
    };
    stopRef.current = stopPolling;

    const tick = (fireNow: boolean) => {
      if (cancel() || stopped || document.hidden) return;
      // Retry/đổi import vẫn phải chờ request cũ hoàn tất để không poll chồng.
      if (inFlight.current) {
        pendingTimer = window.setTimeout(() => tick(fireNow), POLL_INTERVAL_MS);
        return;
      }
      inFlight.current = true;
      if (!fireNow) {
        pollCountRef.current += 1;
      }
      void pollRef.current(importId)
        .then((snapshot) => {
          if (cancel()) return;
          stopTimer();
          onUpdateRef.current(snapshot);
          if (cancel()) return;
          setUiState((current) => ({ ...current, pollError: false }));
          if (!isProcessingRef.current(getStatusRef.current(snapshot))) {
            stopped = true;
            return;
          }
          if (pollCountRef.current >= MAX_POLL_COUNT) {
            stopped = true;
            setUiState((current) => ({ ...current, stalled: true }));
            return;
          }
          if (document.hidden) return;
          pendingTimer = window.setTimeout(() => tick(false), POLL_INTERVAL_MS);
        })
        .catch((error: unknown) => {
          if (cancel()) return;
          stopTimer();
          setUiState((current) => ({ ...current, pollError: true }));
          pausedOnError = true;
          onErrorRef.current(error);
        })
        .finally(() => {
          inFlight.current = false;
        });
    };

    const handleVisibility = () => {
      if (!active) return;
      if (document.hidden) {
        stopTimer();
        return;
      }
      if (pausedOnError || stopped) return;
      stopTimer();
      tick(true);
    };

    if (!document.hidden) tick(true);
    document.addEventListener("visibilitychange", handleVisibility);
    return stopPolling;
  }, [enabled, importId, retryKey]);

  const retry = useCallback(() => {
    pollCountRef.current = 0;
    setUiState({ importId, pollError: false, stalled: false });
    setRetryKey((key) => key + 1);
  }, [importId]);

  const stop = useCallback(() => {
    // Chặn cả response đang bay về, không phải đợi effect cleanup.
    stopRef.current();
    pollCountRef.current = 0;
    setUiState({ importId: null, stalled: false, pollError: false });
  }, []);

  const isCurrentImport = uiState.importId === importId;
  return {
    stalled: isCurrentImport && uiState.stalled,
    pollError: isCurrentImport && uiState.pollError,
    retry,
    stop,
  };
}
