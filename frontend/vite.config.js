import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// API path prefixes served by the FastAPI backend.
const API_PREFIXES = [
  "/auth",
  "/transactions",
  "/categories",
  "/budgets",
  "/recurring",
  "/goals",
  "/reports",
  "/import",
  "/export",
  "/chat",
  "/ai",
  "/health",
];

// Some prefixes (/budgets, /goals, /chat) are ALSO client-side routes.
// A browser navigating there sends a document request (Accept: text/html); that
// must reach the SPA, not the backend. XHR/fetch API calls send Accept: */* or
// application/json. The bypass routes document requests back to index.html and
// proxies only genuine API calls.
const bypass = (req) => {
  const accept = req.headers.accept || "";
  if (req.method === "GET" && accept.includes("text/html")) {
    return "/index.html";
  }
  return null; // proxy it
};

const proxy = Object.fromEntries(
  API_PREFIXES.map((p) => [p, { target: "http://localhost:8000", changeOrigin: true, bypass }]),
);

export default defineConfig({
  plugins: [react()],
  server: { proxy },
});
