import { spawn } from "node:child_process";
import { existsSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const currentDir = dirname(fileURLToPath(import.meta.url));
const backendDir = resolve(currentDir, "../../backend");
const port = process.env.QIYAN_E2E_BACKEND_PORT ?? "8000";

const candidates =
  process.platform === "win32"
    ? [
        join(backendDir, ".uv-test-venv", "Scripts", "python.exe"),
        join(backendDir, ".venv", "Scripts", "python.exe"),
      ]
    : [
        join(backendDir, ".uv-test-venv", "bin", "python"),
        join(backendDir, ".venv", "bin", "python"),
      ];

const pythonCommand = candidates.find((candidate) => existsSync(candidate)) ?? "python";

const child = spawn(
  pythonCommand,
  ["-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", port],
  {
    cwd: backendDir,
    env: {
      ...process.env,
      PYTHONIOENCODING: "utf-8",
      PYTHONUTF8: "1",
      QIYAN_ACCESS_TOKENS: "",
      LITERATURE_RUNTIME_STATE_PATH: join(tmpdir(), "qiyan-e2e-runtime.json"),
      CHUNK_RUNTIME_STATE_PATH: join(tmpdir(), "qiyan-e2e-chunks.json"),
      NETWORK_TASKS_RUNTIME_STATE_PATH: join(tmpdir(), "qiyan-e2e-network-tasks.json"),
      VECTOR_INDEX_RUNTIME_CACHE_PATH: join(tmpdir(), "qiyan-e2e-vector-index.npy"),
      UPLOAD_STORAGE_DIR: join(tmpdir(), "qiyan-e2e-uploads"),
    },
    shell: false,
    stdio: "inherit",
  },
);

const forwardSignal = (signal) => {
  // On POSIX, signals propagate to the child group naturally.
  // On Windows, `child.kill()` only signals the immediate uvicorn process;
  // its multiprocessing.spawn worker that actually owns :8000 is orphaned.
  // `taskkill /T /F /PID` walks the process tree and kills descendants too.
  if (process.platform === "win32" && child.pid) {
    spawn("taskkill", ["/T", "/F", "/PID", String(child.pid)], {
      stdio: "ignore",
      shell: false,
    });
    return;
  }
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
