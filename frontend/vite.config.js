import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Dev proxy: forward API calls to the FastAPI backend on :8000.
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      "/auth": "http://localhost:8000",
      "/transactions": "http://localhost:8000",
      "/categories": "http://localhost:8000",
      "/budgets": "http://localhost:8000",
      "/recurring": "http://localhost:8000",
      "/chat": "http://localhost:8000",
      "/ai": "http://localhost:8000",
    },
  },
});
