# BudgetFlow — Frontend

React + Vite SPA. **Phase 3** of the [plan](../IMPLEMENTATION_PLAN.md): auth, dashboard, ledger, budgets, and the AI assistant UI.

## Design

A ledger/paper-register aesthetic — warm paper ground, ink-teal, a single ochre accent. Money is set in a tabular monospace so figures align like an accountant's column; hairline rules separate entries. Income reads green, expenses rust.

## Run (dev)

```bash
cd frontend
npm install
npm run dev          # http://localhost:5173
```

The dev server proxies `/auth`, `/transactions`, `/categories`, `/budgets`, `/recurring`, `/chat`, `/ai` to the backend at `http://localhost:8000` (see `vite.config.js`). Start the backend first.

## Pages

- **Overview** — month income/spent/net cards + spend-by-category donut and top categories.
- **Ledger** — transactions list with inline add and soft delete; AI/auto entries are tagged.
- **Budgets** — set monthly category limits; progress bars turn ochre at 80%, rust when over.
- **Assistant** — chat with a provider switcher (Groq/Gemini/HF) and multi-turn sessions. NL-add, spending Q&A, and insights all route through `POST /chat`.

## Auth

JWT access + refresh in `localStorage`; an Axios interceptor refreshes on 401 and replays the request, redirecting to `/login` if refresh fails.

## Build / deploy

```bash
npm run build        # -> dist/
```

Deploy `dist/` to Vercel. `vercel.json` rewrites all routes to `index.html` for SPA routing. Point API paths at your Render backend via a Vercel rewrite or same-domain hosting.
