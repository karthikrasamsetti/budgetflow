import { NavLink, Navigate, Route, Routes, useNavigate } from "react-router-dom";
import { useAuth } from "./context/AuthContext";
import WakingBanner from "./components/WakingBanner";
import Login from "./pages/Login";
import Dashboard from "./pages/Dashboard";
import Transactions from "./pages/Transactions";
import Budgets from "./pages/Budgets";
import Goals from "./pages/Goals";
import Chat from "./pages/Chat";

function Shell({ children }) {
  const { user, logout } = useAuth();
  const nav = useNavigate();
  const link = ({ isActive }) => ({
    textDecoration: "none",
    fontWeight: 500,
    padding: "6px 2px",
    borderBottom: isActive ? "2px solid var(--ochre)" : "2px solid transparent",
    color: isActive ? "var(--ink)" : "var(--ink-soft)",
  });
  return (
    <div style={{ maxWidth: 960, margin: "0 auto", padding: "0 20px 60px" }}>
      <header
        style={{
          display: "flex",
          alignItems: "center",
          gap: 24,
          padding: "22px 0 18px",
          borderBottom: "1px solid var(--line)",
          marginBottom: 28,
          flexWrap: "wrap",
        }}
      >
        <div
          style={{ fontFamily: "var(--display)", fontSize: 22, fontWeight: 600, marginRight: 8 }}
        >
          Budget<span style={{ color: "var(--ochre)" }}>Flow</span>
        </div>
        <nav style={{ display: "flex", gap: 18 }}>
          <NavLink to="/" style={link} end>
            Overview
          </NavLink>
          <NavLink to="/transactions" style={link}>
            Ledger
          </NavLink>
          <NavLink to="/budgets" style={link}>
            Budgets
          </NavLink>
          <NavLink to="/goals" style={link}>
            Goals
          </NavLink>
          <NavLink to="/chat" style={link}>
            Assistant
          </NavLink>
        </nav>
        <div style={{ marginLeft: "auto", display: "flex", alignItems: "center", gap: 12 }}>
          <span className="muted" style={{ fontSize: 13 }}>
            {user?.email}
          </span>
          <button
            className="btn ghost small"
            onClick={() => {
              logout();
              nav("/login");
            }}
          >
            Sign out
          </button>
        </div>
      </header>
      {children}
    </div>
  );
}

function Protected({ children }) {
  const { user, ready } = useAuth();
  if (!ready) return <div style={{ padding: 40 }}>Loading…</div>;
  if (!user) return <Navigate to="/login" replace />;
  return <Shell>{children}</Shell>;
}

export default function App() {
  const { user, ready } = useAuth();
  return (
    <>
      <WakingBanner />
      <Routes>
        <Route
          path="/login"
          element={ready && user ? <Navigate to="/" replace /> : <Login />}
        />
        <Route path="/" element={<Protected><Dashboard /></Protected>} />
        <Route path="/transactions" element={<Protected><Transactions /></Protected>} />
        <Route path="/budgets" element={<Protected><Budgets /></Protected>} />
        <Route path="/goals" element={<Protected><Goals /></Protected>} />
        <Route path="/chat" element={<Protected><Chat /></Protected>} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </>
  );
}