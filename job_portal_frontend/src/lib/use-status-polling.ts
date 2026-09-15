"use client";

import { useCallback, useEffect, useRef, useState } from "react";

const POLL_INTERVAL_MS = 2000;
// Không tính thời gian tab bị ẩn.
const MAX_ACTIVE_MS = 120_000;

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
  const activeMsRef = useRef(0);

  if (importId !== uiState.importId) {
    setUiState({ importId, stalled: false, pollError: false });
  }

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
    activeMsRef.current = 0;
  }, [importId]);

  useEffect(() => {
    if (!enabled || !importId) return;
    let active = true;
    let inFlight = false;
    let pendingTimer: number | undefined;
    let pausedOnError = false;

    const stopTimer = () => {
      if (pendingTimer !== undefined) {
        window.clearTimeout(pendingTimer);
        pendingTimer = undefined;
      }
    };

    const cancel = () => !active || !enabled;

    const tick = (fireNow: boolean) => {
      if (cancel() || inFlight) return;
      inFlight = true;
      if (!fireNow) {
        activeMsRef.current += POLL_INTERVAL_MS;
      }
      void pollRef.current(importId)
        .then((snapshot) => {
          if (cancel()) return;
          inFlight = false;
          onUpdateRef.current(snapshot);
          setUiState((current) => ({ ...current, pollError: false }));
          if (!isProcessingRef.current(getStatusRef.current(snapshot))) {
            return;
          }
          if (activeMsRef.current >= MAX_ACTIVE_MS) {
            setUiState((current) => ({ ...current, stalled: true }));
            return;
          }
          if (document.hidden) return;
          pendingTimer = window.setTimeout(() => tick(false), POLL_INTERVAL_MS);
        })
        .catch((error: unknown) => {
          if (cancel()) return;
          inFlight = false;
          setUiState((current) => ({ ...current, pollError: true }));
          pausedOnError = true;
          onErrorRef.current(error);
        });
    };

    const handleVisibility = () => {
      if (!active) return;
      if (document.hidden) {
        stopTimer();
        return;
      }
      if (inFlight || pausedOnError) return;
      tick(true);
    };

    if (!document.hidden) tick(true);
    document.addEventListener("visibilitychange", handleVisibility);
    return () => {
      active = false;
      stopTimer();
      document.removeEventListener("visibilitychange", handleVisibility);
    };
  }, [enabled, importId, retryKey]);

  const retry = useCallback(() => {
    activeMsRef.current = 0;
    setUiState((current) => ({ ...current, pollError: false, stalled: false }));
    setRetryKey((key) => key + 1);
  }, []);

  return { stalled: uiState.stalled, pollError: uiState.pollError, retry };
}
