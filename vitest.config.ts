import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  test: {
    environment: "jsdom",
    globals: false,
    setupFiles: ["./web/src/test-setup.ts"],
    include: ["web/src/**/*.test.{ts,tsx}"],
    css: false,
  },
});
