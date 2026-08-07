import { useEffect, useMemo, useState } from "react";
import api from "../api/client";
import { fmt, today } from "../api/format";
import { useAuth } from "../context/AuthContext";

export default function Transactions() {
  const { user } = useAuth();
  const cur = user?.currency || "INR";
  const [txs, setTxs] = useState([]);
  const [cats, setCats] = useState([]);
  const [form, setForm] = useState({
    amount: "",
    kind: "expense",
    occurred_on: today(),
    category_id: "",
  });
  const [busy, setBusy] = useState(false);

  const load = () =>
    api.get("/transactions?limit=500").then((r) => setTxs(r.data));

  useEffect(() => {
    load();
    api.get("/categories").then((r) => setCats(r.data));
  }, []);

  const catName = useMemo(() => {
    const m = {};
    cats.forEach((c) => (m[c.id] = c.name));
    return m;
  }, [cats]);

  const add = async (e) => {
    e.preventDefault();
    setBusy(true);
    try {
      await api.post("/transactions", {
        amount: form.amount,
        kind: form.kind,
        occurred_on: form.occurred_on,
        category_id: form.category_id ? Number(form.category_id) : null,
      });
      setForm({ ...form, amount: "", category_id: "" });
      await load();
    } finally {
      setBusy(false);
    }
  };

  const remove = async (id) => {
    await api.delete(`/transactions/${id}`);
    setTxs((t) => t.filter((x) => x.id !== id));
  };

  const exportCsv = async () => {
    const r = await api.get("/export/csv", { responseType: "blob" });
    const url = URL.createObjectURL(r.data);
    const a = document.createElement("a");
    a.href = url;
    a.download = "transactions.csv";
    a.click();
    URL.revokeObjectURL(url);
  };

  const importCsv = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const text = await file.text();
    await api.post("/import/csv", text, { headers: { "Content-Type": "text/csv" } });
    e.target.value = "";
    await load();
  };

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 18 }}>
        <h1 style={{ fontSize: 30 }}>Ledger</h1>
        <div style={{ display: "flex", gap: 8 }}>
          <button className="btn ghost small" onClick={exportCsv}>
            Export CSV
          </button>
          <label className="btn ghost small" style={{ margin: 0 }}>
            Import CSV
            <input type="file" accept=".csv" onChange={importCsv} style={{ display: "none" }} />
          </label>
        </div>
      </div>

      <form
        onSubmit={add}
        className="card"
        style={{
          display: "grid",
          gridTemplateColumns: "1fr 120px 130px 1fr auto",
          gap: 12,
          alignItems: "end",
          marginBottom: "var(--gap)",
        }}
      >
        <div>
          <label>Amount</label>
          <input
            type="number"
            step="0.01"
            min="0.01"
            value={form.amount}
            onChange={(e) => setForm({ ...form, amount: e.target.value })}
            required
          />
        </div>
        <div>
          <label>Type</label>
          <select value={form.kind} onChange={(e) => setForm({ ...form, kind: e.target.value })}>
            <option value="expense">Expense</option>
            <option value="income">Income</option>
          </select>
        </div>
        <div>
          <label>Date</label>
          <input
            type="date"
            value={form.occurred_on}
            onChange={(e) => setForm({ ...form, occurred_on: e.target.value })}
          />
        </div>
        <div>
          <label>Category</label>
          <select
            value={form.category_id}
            onChange={(e) => setForm({ ...form, category_id: e.target.value })}
          >
            <option value="">Uncategorized</option>
            {cats
              .filter((c) => c.kind === form.kind)
              .map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name}
                </option>
              ))}
          </select>
        </div>
        <button className="btn" disabled={busy}>
          Add entry
        </button>
      </form>

      <div className="card" style={{ padding: 0, overflow: "hidden" }}>
        <table className="ledger">
          <thead>
            <tr>
              <th>Date</th>
              <th>Category</th>
              <th>Note</th>
              <th className="num">Amount</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {txs.map((t) => (
              <tr key={t.id}>
                <td className="muted" style={{ fontFamily: "var(--mono)", fontSize: 13 }}>
                  {t.occurred_on}
                </td>
                <td>
                  {catName[t.category_id] || <span className="muted">—</span>}
                  {t.source === "ai" && <span className="pill" style={{ marginLeft: 8 }}>AI</span>}
                  {t.source === "recurring" && (
                    <span className="pill" style={{ marginLeft: 8 }}>auto</span>
                  )}
                </td>
                <td className="muted">{t.note || ""}</td>
                <td className={`num money ${t.kind === "income" ? "pos" : "neg"}`}>
                  {t.kind === "income" ? "+" : "−"}
                  {fmt(t.amount, cur).replace(/^[^\d]*/, "")}
                </td>
                <td className="num">
                  <button className="btn ghost small" onClick={() => remove(t.id)}>
                    Delete
                  </button>
                </td>
              </tr>
            ))}
            {txs.length === 0 && (
              <tr>
                <td colSpan={5} className="muted" style={{ padding: 24, textAlign: "center" }}>
                  No entries yet. Add your first above, or ask the Assistant.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
