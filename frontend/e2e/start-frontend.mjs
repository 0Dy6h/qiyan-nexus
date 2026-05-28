import { spawn } from "node:child_process";

const port = process.env.QIYAN_E2E_FRONTEND_PORT ?? "3000";
const backendPort = process.env.QIYAN_E2E_BACKEND_PORT ?? "8000";

const pnpmEntrypoint = process.env.npm_execpath;
const command = pnpmEntrypoint ? process.execPath : process.platform === "win32" ? "pnpm.cmd" : "pnpm";
const args = pnpmEntrypoint
  ? [pnpmEntrypoint, "dev", "--hostname", "127.0.0.1", "--port", port]
  : ["dev", "--hostname", "127.0.0.1", "--port", port];

const child = spawn(command, args, {
  env: {
    ...process.env,
    NEXT_PUBLIC_API_BASE_URL: `http://127.0.0.1:${backendPort}`,
  },
  shell: false,
  stdio: "inherit",
});

const forwardSignal = (signal) => {
  child.kill(signal);
};

process.on("SIGINT", forwardSignal);
process.on("SIGTERM", forwardSignal);

child.on("exit", (code, signal) => {
  if (signal) {
    process.kill(process.pid, signal);
    return;
  }
  process.exit(code ?? 0);
});
