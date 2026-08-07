import { useEffect, useRef, useState } from "react";
import api from "../api/client";

export default function Chat() {
  const [providers, setProviders] = useState([]);
  const [provider, setProvider] = useState("");
  const [sessionId, setSessionId] = useState(null);
  const [msgs, setMsgs] = useState([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const endRef = useRef(null);
  const [usage, setUsage] = useState(null);

  const loadUsage = () => api.get("/ai/usage").then((r) => setUsage(r.data));

  useEffect(() => {
    api.get("/ai/providers").then((r) => {
      setProviders(r.data.providers);
      const def = r.data.providers.find((p) => p.is_default);
      setProvider(def?.name || r.data.providers[0]?.name || "");
    });
    loadUsage();
  }, []);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [msgs]);

  const send = async (e) => {
    e.preventDefault();
    const text = input.trim();
    if (!text) return;
    setInput("");
    setMsgs((m) => [...m, { role: "user", content: text }]);
    setBusy(true);
    try {
      const { data } = await api.post("/chat", {
        message: text,
        session_id: sessionId,
        provider: provider || null,
      });
      setSessionId(data.session_id);
      setMsgs((m) => [
        ...m,
        { role: "assistant", content: data.reply, action: data.action, intent: data.intent },
      ]);
      loadUsage();
    } catch {
      setMsgs((m) => [
        ...m,
        { role: "assistant", content: "The assistant is unavailable right now.", intent: "error" },
      ]);
    } finally {
      setBusy(false);
    }
  };

  const anyConfigured = providers.some((p) => p.configured);

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
        <h1 style={{ fontSize: 30 }}>Assistant</h1>
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <span className="eyebrow">Model</span>
          <select
            value={provider}
            onChange={(e) => setProvider(e.target.value)}
            style={{ width: "auto" }}
          >
            {providers.map((p) => (
              <option key={p.name} value={p.name} disabled={!p.configured}>
                {p.name}
                {!p.configured ? " (no key)" : ""}
              </option>
            ))}
          </select>
        </div>
      </div>

      {!anyConfigured && (
        <div className="card" style={{ marginBottom: 14, borderColor: "var(--ochre)" }}>
          <strong>No provider configured.</strong>{" "}
          <span className="muted">
            Set a Groq, Gemini, or HuggingFace key in the backend .env to enable replies.
            You can still send messages to see routing.
          </span>
        </div>
      )}

      <div
        className="card"
        style={{ minHeight: 340, maxHeight: "58vh", overflowY: "auto", display: "flex", flexDirection: "column", gap: 12 }}
      >
        {msgs.length === 0 && (
          <div className="muted" style={{ margin: "auto", textAlign: "center", maxWidth: 360 }}>
            Try <em>“spent 500 on food yesterday”</em>, or ask{" "}
            <em>“how much did I spend on food this month?”</em>
          </div>
        )}
        {msgs.map((m, i) => (
          <div
            key={i}
            style={{
              alignSelf: m.role === "user" ? "flex-end" : "flex-start",
              maxWidth: "78%",
              background: m.role === "user" ? "var(--ink)" : "var(--paper-2)",
              color: m.role === "user" ? "var(--paper)" : "var(--ink)",
              padding: "10px 14px",
              borderRadius: 12,
              border: m.role === "user" ? "none" : "1px solid var(--line)",
            }}
          >
            {m.content}
            {m.action?.type === "transaction_created" && (
              <div style={{ marginTop: 6 }}>
                <span className="pill">entry recorded</span>
              </div>
            )}
          </div>
        ))}
        {busy && <div className="muted" style={{ alignSelf: "flex-start" }}>…</div>}
        <div ref={endRef} />
      </div>

      <form onSubmit={send} style={{ display: "flex", gap: 10, marginTop: 14 }}>
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Message your ledger…"
          disabled={busy}
        />
        <button className="btn" disabled={busy || !input.trim()}>
          Send
        </button>
      </form>

      {usage && usage.calls > 0 && (
        <div
          className="card"
          style={{ marginTop: 14, display: "flex", gap: 20, flexWrap: "wrap", fontSize: 13 }}
        >
          <span className="eyebrow">Assistant usage</span>
          <span>
            <strong>{usage.calls}</strong> calls
          </span>
          <span>
            <strong>{usage.total_tokens.toLocaleString()}</strong> tokens
          </span>
          <span>
            <strong>{usage.avg_latency_ms}</strong> ms avg
          </span>
          {Object.entries(usage.by_provider).map(([p, n]) => (
            <span key={p} className="pill">
              {p}: {n}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}
