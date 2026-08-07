import { useEffect, useState } from "react";
import api from "../api/client";
import { fmt } from "../api/format";
import { useAuth } from "../context/AuthContext";

export default function Goals() {
  const { user } = useAuth();
  const cur = user?.currency || "INR";
  const [goals, setGoals] = useState([]);
  const [form, setForm] = useState({ name: "", target_amount: "" });
  const [give, setGive] = useState({});

  const load = () => api.get("/goals").then((r) => setGoals(r.data));
  useEffect(() => {
    load();
  }, []);

  const add = async (e) => {
    e.preventDefault();
    await api.post("/goals", { name: form.name, target_amount: form.target_amount });
    setForm({ name: "", target_amount: "" });
    await load();
  };

  const contribute = async (id) => {
    const amount = give[id];
    if (!amount) return;
    await api.post(`/goals/${id}/contribute`, { amount });
    setGive({ ...give, [id]: "" });
    await load();
  };

  const remove = async (id) => {
    await api.delete(`/goals/${id}`);
    await load();
  };

  return (
    <div>
      <h1 style={{ fontSize: 30, marginBottom: 18 }}>Goals</h1>

      <form
        onSubmit={add}
        className="card"
        style={{ display: "grid", gridTemplateColumns: "1fr 180px auto", gap: 12, alignItems: "end", marginBottom: "var(--gap)" }}
      >
        <div>
          <label>Goal</label>
          <input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder="New laptop" required />
        </div>
        <div>
          <label>Target</label>
          <input type="number" step="0.01" min="0.01" value={form.target_amount} onChange={(e) => setForm({ ...form, target_amount: e.target.value })} required />
        </div>
        <button className="btn">Add goal</button>
      </form>

      <div style={{ display: "grid", gap: 12 }}>
        {goals.map((g) => {
          const pct = Math.min((Number(g.saved_amount) / Number(g.target_amount)) * 100, 100);
          const done = pct >= 100;
          return (
            <div className="card" key={g.id}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline" }}>
                <strong>{g.name}</strong>
                <span className="money" style={{ fontSize: 14 }}>
                  {fmt(g.saved_amount, cur)} <span className="muted">/ {fmt(g.target_amount, cur)}</span>
                </span>
              </div>
              <div style={{ height: 10, background: "var(--paper-2)", borderRadius: 6, margin: "10px 0 10px", overflow: "hidden", border: "1px solid var(--line)" }}>
                <div style={{ width: `${pct}%`, height: "100%", background: done ? "var(--green)" : "var(--ochre)", transition: "width .4s ease" }} />
              </div>
              <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
                {done ? (
                  <span className="pill" style={{ color: "var(--green)" }}>reached 🎉</span>
                ) : (
                  <>
                    <input
                      type="number"
                      placeholder="Add amount"
                      value={give[g.id] || ""}
                      onChange={(e) => setGive({ ...give, [g.id]: e.target.value })}
                      style={{ maxWidth: 160 }}
                    />
                    <button className="btn small" onClick={() => contribute(g.id)}>
                      Contribute
                    </button>
                  </>
                )}
                <button className="btn ghost small" style={{ marginLeft: "auto" }} onClick={() => remove(g.id)}>
                  Remove
                </button>
              </div>
            </div>
          );
        })}
        {goals.length === 0 && (
          <div className="card muted" style={{ textAlign: "center", padding: 28 }}>
            No goals yet. Name something you're saving for and set a target.
          </div>
        )}
      </div>
    </div>
  );
}
