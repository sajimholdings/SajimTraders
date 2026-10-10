"use client";

import { useEffect, useRef } from "react";

/**
 * Runs `callback` immediately when enabled, then on a fixed interval.
 *
 * - The callback is read through a ref so the interval is never torn down and
 *   re-created when the callback identity changes.
 * - In-flight guard: a tick is skipped while the previous one is still running.
 * - Each subscription owns an AbortController that is aborted on unmount, when
 *   `enabled` turns false, or when `resetKey` changes (e.g. account switch or
 *   sign-out), so stale requests are cancelled.
 * - Polling pauses while the document is hidden and resumes with an immediate
 *   tick when it becomes visible again.
 */
export function usePolling(
  callback: (signal: AbortSignal) => Promise<void> | void,
  intervalMs: number,
  enabled: boolean,
  resetKey: unknown = null
): void {
  const callbackRef = useRef(callback);

  useEffect(() => {
    callbackRef.current = callback;
  }, [callback]);

  useEffect(() => {
    if (!enabled) return;
    const controller = new AbortController();
    let inFlight = false;

    const tick = async () => {
      if (inFlight || controller.signal.aborted) return;
      if (typeof document !== "undefined" && document.hidden) return;
      inFlight = true;
      try {
        await callbackRef.current(controller.signal);
      } catch {
        // Callbacks are expected to handle their own errors.
      } finally {
        inFlight = false;
      }
    };

    const onVisibility = () => {
      if (!document.hidden) void tick();
    };

    void tick();
    const id = setInterval(() => void tick(), intervalMs);
    if (typeof document !== "undefined") {
      document.addEventListener("visibilitychange", onVisibility);
    }
    return () => {
      clearInterval(id);
      controller.abort();
      if (typeof document !== "undefined") {
        document.removeEventListener("visibilitychange", onVisibility);
      }
    };
  }, [enabled, intervalMs, resetKey]);
}
