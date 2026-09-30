import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// In development the API runs separately on port 8000.
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      "/api": "http://localhost:8000",
      "/samples": "http://localhost:8000",
    },
  },
});
