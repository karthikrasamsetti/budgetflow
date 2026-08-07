import { useEffect, useMemo, useState } from "react";
import api from "../api/client";
import { fmt } from "../api/format";
import { useAuth } from "../context/AuthContext";

export default function Budgets() {
  const { user } = useAuth();
  const cur = user?.currency || "INR";
  const [rows, setRows] = useState([]); // {budget, status}
  const [cats, setCats] = useState([]);
  const [form, setForm] = useState({ category_id: "", amount: "" });

  const load = async () => {
    const [b, c] = await Promise.all([api.get("/budgets"), api.get("/categories")]);
    setCats(c.data);
    const withStatus = await Promise.all(
      b.data.map((bud) =>
        api.get(`/budgets/${bud.id}/status`).then((s) => s.data),
      ),
    );
    setRows(withStatus);
  };

  useEffect(() => {
    load();
  }, []);

  const catName = useMemo(() => {
    const m = {};
    cats.forEach((c) => (m[c.id] = c.name));
    return m;
  }, [cats]);

  const add = async (e) => {
    e.preventDefault();
    await api.post("/budgets", {
      category_id: Number(form.category_id),
      amount: form.amount,
    });
    setForm({ category_id: "", amount: "" });
    await load();
  };

  const remove = async (id) => {
    await api.delete(`/budgets/${id}`);
    await load();
  };

  const expenseCats = cats.filter((c) => c.kind === "expense");

  return (
    <div>
      <h1 style={{ fontSize: 30, marginBottom: 18 }}>Budgets</h1>

      <form
        onSubmit={add}
        className="card"
        style={{
          display: "grid",
          gridTemplateColumns: "1fr 160px auto",
          gap: 12,
          alignItems: "end",
          marginBottom: "var(--gap)",
        }}
      >
        <div>
          <label>Category</label>
          <select
            value={form.category_id}
            onChange={(e) => setForm({ ...form, category_id: e.target.value })}
            required
          >
            <option value="">Choose…</option>
            {expenseCats.map((c) => (
              <option key={c.id} value={c.id}>
                {c.name}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label>Monthly limit</label>
          <input
            type="number"
            step="0.01"
            min="0.01"
            value={form.amount}
            onChange={(e) => setForm({ ...form, amount: e.target.value })}
            required
          />
        </div>
        <button className="btn">Set budget</button>
      </form>

      <div style={{ display: "grid", gap: 12 }}>
        {rows.map(({ budget, spent, remaining, ratio, alerts }) => {
          const pct = Math.min(ratio * 100, 100);
          const over = ratio >= 1;
          const warn = alerts.includes(0.8) && !over;
          const barColor = over ? "var(--rust)" : warn ? "var(--ochre)" : "var(--green)";
          return (
            <div className="card" key={budget.id}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline" }}>
                <strong>{catName[budget.category_id] || "Category"}</strong>
                <span className="money" style={{ fontSize: 14 }}>
                  {fmt(spent, cur)} <span className="muted">/ {fmt(budget.amount, cur)}</span>
                </span>
              </div>
              <div
                style={{
                  height: 10,
                  background: "var(--paper-2)",
                  borderRadius: 6,
                  margin: "10px 0 8px",
                  overflow: "hidden",
                  border: "1px solid var(--line)",
                }}
              >
                <div
                  style={{
                    width: `${pct}%`,
                    height: "100%",
                    background: barColor,
                    transition: "width .4s ease",
                  }}
                />
              </div>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <span style={{ fontSize: 13 }}>
                  {over ? (
                    <span style={{ color: "var(--rust)" }}>Over by {fmt(-remaining, cur)}</span>
                  ) : warn ? (
                    <span style={{ color: "#a5772a" }}>Nearing limit · {fmt(remaining, cur)} left</span>
                  ) : (
                    <span className="muted">{fmt(remaining, cur)} left</span>
                  )}
                </span>
                <button className="btn ghost small" onClick={() => remove(budget.id)}>
                  Remove
                </button>
              </div>
            </div>
          );
        })}
        {rows.length === 0 && (
          <div className="card muted" style={{ textAlign: "center", padding: 28 }}>
            No budgets set. Choose a category and a monthly limit to start tracking.
          </div>
        )}
      </div>
    </div>
  );
}
