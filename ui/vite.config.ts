import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// API paths are proxied to the locally running API (python -m api), so the
// browser only ever talks to the dev server and no CORS setup is needed.
const API_URL = process.env.TENDERPY_API_URL ?? "http://127.0.0.1:8000";

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      "/api": {
        target: API_URL,
        rewrite: (path) => path.replace(/^\/api/, ""),
      },
    },
  },
});
