import { defineConfig, devices } from "@playwright/test";

const FRONTEND_PORT = 3000;
const BACKEND_PORT = 8000;
const FRONTEND_URL = `http://127.0.0.1:${FRONTEND_PORT}`;
const BACKEND_URL = `http://127.0.0.1:${BACKEND_PORT}`;
const hasE2EAccessToken = Boolean(process.env.QIYAN_E2E_ACCESS_TOKEN?.trim());

export default defineConfig({
  testDir: "./e2e",
  timeout: 60_000,
  expect: { timeout: 10_000 },
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: 0,
  workers: 1,
  reporter: process.env.CI ? "line" : "list",
  use: {
    baseURL: FRONTEND_URL,
    trace: "retain-on-failure",
    video: "off",
    screenshot: "only-on-failure",
  },
  projects: [
    { name: "chromium", use: { ...devices["Desktop Chrome"] } },
  ],
  webServer: [
    {
      // Backend dev server — isolated runtime state + open access (no token).
      command: "node ./e2e/start-backend.mjs",
      url: `${BACKEND_URL}/health`,
      reuseExistingServer: !hasE2EAccessToken && !process.env.CI,
      timeout: 60_000,
    },
    {
      command: "node ./e2e/start-frontend.mjs",
      url: FRONTEND_URL,
      reuseExistingServer: !hasE2EAccessToken && !process.env.CI,
      timeout: 120_000,
    },
  ],
});
