/**
 * Sajim Traders — Client-Side Action & Event Logger
 * Dispatches every user action to the server log endpoint for live auditing.
 */

export function trackAction(event: string, details: Record<string, any> = {}) {
  try {
    const payload = {
      event,
      details,
      timestamp: new Date().toISOString(),
      url: typeof window !== "undefined" ? window.location.href : "",
    };

    if (process.env.NODE_ENV !== "production") {
      console.log(`[CLIENT_ACTION] ${event}`, details);
    }

    // Attempt beacon dispatch or fallback to fetch
    if (typeof navigator !== "undefined" && typeof navigator.sendBeacon === "function") {
      const blob = new Blob([JSON.stringify(payload)], { type: "application/json" });
      navigator.sendBeacon("/api/client/log", blob);
    } else {
      fetch("/api/client/log", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      }).catch(() => {});
    }
  } catch {
    // Fail silently in browser
  }
}
