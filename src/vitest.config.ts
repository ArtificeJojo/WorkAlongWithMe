import { defineConfig } from "vitest/config";
import { loadEnv } from "vite";
import path from "node:path";

export default defineConfig(({ mode }) => ({
  resolve: { alias: { "@": path.resolve(__dirname, ".") } },
  test: {
    include: ["tests/**/*.test.ts"],
    // Loads DATABASE_URL from .env.local so the database tests can connect.
    env: loadEnv(mode, process.cwd(), ""),
    fileParallelism: false,
    testTimeout: 20000,
  },
}));
