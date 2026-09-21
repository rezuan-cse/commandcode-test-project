import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

/**
 * Test configuration.
 *
 * Kept separate from `vite.config.ts` so the build settings stay untouched.
 *
 * `env` matters more than it looks. React picks its development or production
 * build from NODE_ENV when it loads, and the production build omits act(), which
 * @testing-library/react requires. A machine that exports NODE_ENV=production
 * (as this one does) would otherwise fail every component test, so the value is
 * pinned here rather than inherited from the shell.
 */
export default defineConfig({
  plugins: [react()],
  test: {
    env: { NODE_ENV: "test" },
    // The component test opts into jsdom with a per-file docblock; unit tests
    // such as the formatting suite stay on the faster node environment.
    environment: "node",
  },
});

