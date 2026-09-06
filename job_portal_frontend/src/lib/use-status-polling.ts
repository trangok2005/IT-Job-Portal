"use client";

import { useCallback, useEffect, useRef, useState } from "react";

const POLL_INTERVAL_MS = 2000;
// Giới hạn thời gian HOẠT ĐỘNG (không tính lúc tab ẩn) trước khi dừng.
const MAX_ACTIVE_MS = 120_000;

type StatusPollingOptions<T, S> = {
  /** Bật polling khi có import đang xử lý. `importId` dùng để reset trạng thái. */
  enabled: boolean;
  importId: string | null;
  /** Hàm gọi API lấy toàn bộ snapshot (DTO) hiện tại. */
  poll: (importId: string) => Promise<T>;
  /** Trích xuất giá trị trạng thái từ snapshot để điều khiển vòng lặp. */
  getStatus: (snapshot: T) => S;
  /** Kiểm tra trạng thái có còn đang xử lý hay không. */
  isProcessing: (status: S) => boolean;
  /** Được gọi sau mỗi request thành công với snapshot mới nhất. */
  onUpdate: (snapshot: T) => void;
  /** Được gọi khi request gặp lỗi mạng; không xóa import ID khỏi localStorage. */
  onError: (error: unknown) => void;
};

type PollUiState = {
  importId: string | null;
  stalled: boolean;
  pollError: boolean;
};

/**
 * Poll trạng thái trích xuất (CV / JD) bằng vòng `setTimeout` tuần tự:
 * - `enabled = true` → kiểm tra NGAY, không đợi 2 giây.
 * - Chỉ lên lịch request tiếp theo sau khi request hiện tại hoàn thành.
 * - Tab ẩn → tạm dừng; quay lại tab → kiểm tra ngay lập tức.
 * - Hết MAX_ACTIVE_MS → dừng, giữ import ID và trả `stalled = true`.
 * - Import ID mới → reset error / stalled / thời gian theo dõi.
 * - Lỗi mạng → dừng tạm, gọi onError để UI cung cấp nút "Thử lại".
 */
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

  // Điều chỉnh state trong render để request đầu tiên của import mới có đủ thời gian.
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
