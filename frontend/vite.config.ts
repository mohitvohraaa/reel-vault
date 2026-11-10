import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

const API_TARGET = process.env.VITE_API_PROXY || "http://localhost:8000";

export default defineConfig({
  plugins: [react()],
  server: {
    host: true,
    port: 5173,
    proxy: {
      "/api": { target: API_TARGET, changeOrigin: true },
      "/health": { target: API_TARGET, changeOrigin: true },
    },
  },
  preview: { host: true, port: 5173 },
});
