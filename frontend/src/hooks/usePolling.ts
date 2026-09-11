"use client";

import { useEffect, useRef } from "react";

/**
 * Runs `callback` immediately when enabled, then on a fixed interval.
 *
 * The callback is read through a ref so the interval is never torn down and
 * re-created when the callback identity changes (e.g. because it closes over
 * changing state). Only `enabled` and `intervalMs` affect the subscription.
 */
export function usePolling(
  callback: () => void,
  intervalMs: number,
  enabled: boolean
): void {
  const callbackRef = useRef(callback);

  useEffect(() => {
    callbackRef.current = callback;
  }, [callback]);

  useEffect(() => {
    if (!enabled) return;
    callbackRef.current();
    const id = setInterval(() => callbackRef.current(), intervalMs);
    return () => clearInterval(id);
  }, [enabled, intervalMs]);
}
