import { useEffect, useState } from "react";

/**
 * Shows a small banner when a request is slow — typically Render's free-tier
 * cold start (~30-50s). Listens for the "bf:waking" event from the API client.
 */
export default function WakingBanner() {
  const [waking, setWaking] = useState(false);

  useEffect(() => {
    const onWake = (e) => setWaking(e.detail);
    window.addEventListener("bf:waking", onWake);
    return () => window.removeEventListener("bf:waking", onWake);
  }, []);

  if (!waking) return null;

  return (
    <div
      style={{
        position: "fixed",
        top: 0,
        left: 0,
        right: 0,
        zIndex: 1000,
        background: "var(--ink)",
        color: "var(--paper)",
        fontSize: 13,
        textAlign: "center",
        padding: "8px 12px",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        gap: 10,
      }}
    >
      <span
        style={{
          width: 12,
          height: 12,
          border: "2px solid var(--ochre)",
          borderTopColor: "transparent",
          borderRadius: "50%",
          display: "inline-block",
          animation: "bf-spin 0.8s linear infinite",
        }}
      />
      Waking the server… the free tier sleeps when idle, so the first request
      takes a moment.
      <style>{`@keyframes bf-spin { to { transform: rotate(360deg); } }`}</style>
    </div>
  );
}