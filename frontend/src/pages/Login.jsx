import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

export default function Login() {
  const { login, register } = useAuth();
  const nav = useNavigate();
  const [mode, setMode] = useState("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    setErr("");
    setBusy(true);
    try {
      if (mode === "login") await login(email, password);
      else await register(email, password);
      nav("/");
    } catch (e2) {
      setErr(e2.response?.data?.detail || "Something went wrong. Try again.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div
      style={{
        minHeight: "100vh",
        display: "grid",
        gridTemplateColumns: "1.1fr 1fr",
        alignItems: "stretch",
      }}
      className="login-grid"
    >
      {/* Hero: a ledger leaf */}
      <div
        style={{
          background: "var(--ink)",
          color: "var(--paper)",
          padding: "56px 48px",
          display: "flex",
          flexDirection: "column",
          justifyContent: "center",
        }}
      >
        <div className="eyebrow" style={{ color: "var(--ochre)" }}>
          A clear account
        </div>
        <h1 style={{ fontSize: 44, lineHeight: 1.05, margin: "14px 0 20px", color: "var(--paper)" }}>
          Your money,
          <br />
          entry by entry.
        </h1>
        <div
          style={{
            fontFamily: "var(--mono)",
            fontSize: 14,
            borderTop: "1px solid rgba(244,241,233,.25)",
          }}
        >
          {[
            ["Salary", "+82,000.00"],
            ["Rent", "−24,000.00"],
            ["Groceries", "−6,480.00"],
            ["Freelance", "+15,500.00"],
          ].map(([k, v]) => (
            <div
              key={k}
              style={{
                display: "flex",
                justifyContent: "space-between",
                padding: "12px 0",
                borderBottom: "1px solid rgba(244,241,233,.15)",
              }}
            >
              <span style={{ opacity: 0.85 }}>{k}</span>
              <span style={{ color: v[0] === "+" ? "var(--ochre)" : "var(--paper)" }}>{v}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Form */}
      <div style={{ display: "flex", alignItems: "center", justifyContent: "center", padding: 32 }}>
        <form onSubmit={submit} style={{ width: "100%", maxWidth: 340 }}>
          <div style={{ fontFamily: "var(--display)", fontSize: 24, marginBottom: 4 }}>
            Budget<span style={{ color: "var(--ochre)" }}>Flow</span>
          </div>
          <p className="muted" style={{ marginTop: 0, marginBottom: 24 }}>
            {mode === "login" ? "Welcome back." : "Open your ledger."}
          </p>

          <div style={{ marginBottom: 14 }}>
            <label>Email</label>
            <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
          </div>
          <div style={{ marginBottom: 18 }}>
            <label>Password</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              minLength={8}
              required
            />
          </div>

          {err && <div className="error" style={{ marginBottom: 12 }}>{err}</div>}

          <button className="btn" style={{ width: "100%" }} disabled={busy}>
            {busy ? "…" : mode === "login" ? "Sign in" : "Create account"}
          </button>

          <button
            type="button"
            className="btn ghost small"
            style={{ width: "100%", marginTop: 10, border: "none" }}
            onClick={() => {
              setMode(mode === "login" ? "register" : "login");
              setErr("");
            }}
          >
            {mode === "login" ? "Need an account? Register" : "Have an account? Sign in"}
          </button>
        </form>
      </div>

      <style>{`@media (max-width: 720px){ .login-grid{ grid-template-columns:1fr !important; } .login-grid>div:first-child{ padding:36px 28px; } }`}</style>
    </div>
  );
}
