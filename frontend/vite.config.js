import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    // During `npm run dev`, forward API calls to the FastAPI backend
    proxy: { "/api": "http://localhost:8004" },
  },
});
