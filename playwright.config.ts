import { defineConfig, devices } from "@playwright/test";

// Resolve the target environment. By default the suite runs against the
// live Vercel deployment so it works without a local dev server. Set
// `E2E_BASE_URL` to a local URL (e.g. http://localhost:5173) to run against
// a Vite preview or `npm run dev`.
const baseURL = process.env.E2E_BASE_URL ?? "https://ad-gen-eng-kfso.vercel.app";

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: process.env.CI ? [["list"], ["html", { open: "never" }]] : "list",
  use: {
    baseURL,
    trace: "on-first-retry",
    screenshot: "only-on-failure",
    video: "off",
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
});
