import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

declare const process: { env: Record<string, string | undefined> };

export default defineConfig({
  plugins: [react()],
  server: { proxy: { "/api": `http://127.0.0.1:${process.env.RAG_API_PORT ?? 3001}` } },
  test: { environment: "jsdom", css: { include: /theme\.css/ } },
});
