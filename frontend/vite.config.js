import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// `npm run dev` serves the page on :5173 and forwards /api calls to chat_server.py on :8000.
// `npm run build` writes frontend/dist, which chat_server.py serves directly.
export default defineConfig({
  plugins: [react()],
  server: { proxy: { "/api": "http://localhost:8000" } },
});
