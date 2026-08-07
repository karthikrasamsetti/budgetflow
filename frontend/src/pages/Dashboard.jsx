import { useEffect, useMemo, useState } from "react";
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from "recharts";
import api from "../api/client";
import { fmt, thisMonth } from "../api/format";
import { useAuth } from "../context/AuthContext";

const SLICE = ["#12403c", "#e8b04b", "#b8543a", "#2f7d5b", "#7a7160", "#3a5b57", "#c98a3a"];

export default function Dashboard() {
  const { user } = useAuth();
  const cur = user?.currency || "INR";
  const [txs, setTxs] = useState([]);
  const [cats, setCats] = useState([]);

  useEffect(() => {
    Promise.all([api.get("/transactions?limit=500"), api.get("/categories")]).then(
      ([t, c]) => {
        setTxs(t.data);
        setCats(c.data);
      },
    );
  }, []);

  const catName = useMemo(() => {
    const m = {};
    cats.forEach((c) => (m[c.id] = c.name));
    return m;
  }, [cats]);

  const month = thisMonth();
  const monthTx = txs.filter((t) => t.occurred_on.startsWith(month));
  const income = monthTx.filter((t) => t.kind === "income").reduce((s, t) => s + +t.amount, 0);
  const expense = monthTx.filter((t) => t.kind === "expense").reduce((s, t) => s + +t.amount, 0);

  const byCat = useMemo(() => {
    const m = {};
    monthTx
      .filter((t) => t.kind === "expense")
      .forEach((t) => {
        const k = catName[t.category_id] || "Uncategorized";
        m[k] = (m[k] || 0) + +t.amount;
      });
    return Object.entries(m)
      .map(([name, value]) => ({ name, value }))
      .sort((a, b) => b.value - a.value);
  }, [monthTx, catName]);

  return (
    <div>
      <div className="eyebrow">This month · {month}</div>
      <h1 style={{ fontSize: 30, margin: "6px 0 22px" }}>Overview</h1>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(3, 1fr)",
          gap: "var(--gap)",
          marginBottom: "var(--gap)",
        }}
        className="stat-grid"
      >
        <Stat label="Income" value={fmt(income, cur)} tone="pos" />
        <Stat label="Spent" value={fmt(expense, cur)} tone="neg" />
        <Stat label="Net" value={fmt(income - expense, cur)} tone={income - expense >= 0 ? "pos" : "neg"} />
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "var(--gap)" }} className="split">
        <div className="card">
          <div className="eyebrow" style={{ marginBottom: 10 }}>
            Where it went
          </div>
          {byCat.length === 0 ? (
            <p className="muted">No expenses yet this month. Add one in the Ledger.</p>
          ) : (
            <ResponsiveContainer width="100%" height={220}>
              <PieChart>
                <Pie data={byCat} dataKey="value" nameKey="name" innerRadius={52} outerRadius={88} paddingAngle={2}>
                  {byCat.map((_, i) => (
                    <Cell key={i} fill={SLICE[i % SLICE.length]} />
                  ))}
                </Pie>
                <Tooltip formatter={(v) => fmt(v, cur)} />
              </PieChart>
            </ResponsiveContainer>
          )}
        </div>

        <div className="card">
          <div className="eyebrow" style={{ marginBottom: 10 }}>
            Top categories
          </div>
          <table className="ledger">
            <tbody>
              {byCat.slice(0, 6).map((r, i) => (
                <tr key={r.name}>
                  <td>
                    <span
                      style={{
                        display: "inline-block",
                        width: 9,
                        height: 9,
                        borderRadius: 2,
                        background: SLICE[i % SLICE.length],
                        marginRight: 8,
                      }}
                    />
                    {r.name}
                  </td>
                  <td className="num money neg">{fmt(r.value, cur)}</td>
                </tr>
              ))}
              {byCat.length === 0 && (
                <tr>
                  <td className="muted">—</td>
                  <td className="num muted">—</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      <style>{`@media(max-width:720px){.stat-grid{grid-template-columns:1fr !important}.split{grid-template-columns:1fr !important}}`}</style>
    </div>
  );
}

function Stat({ label, value, tone }) {
  return (
    <div className="card">
      <div className="eyebrow">{label}</div>
      <div className={`money ${tone}`} style={{ fontSize: 26, marginTop: 6 }}>
        {value}
      </div>
    </div>
  );
}
