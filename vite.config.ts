import { configDefaults, defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    // In development the FastAPI app runs separately (uvicorn on :8000); in production Vercel routes /api to it.
    proxy: { '/api': 'http://127.0.0.1:8000' },
  },
  build: { sourcemap: false, target: 'es2022' },
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./src/test/setup.ts'],
    css: false,
    // Session worktrees live under .claude/; never pick up their copies of the tests.
    exclude: [...configDefaults.exclude, '.claude/**'],
    // Full-page axe scans can take several seconds on slower machines.
    testTimeout: 20_000,
  },
});
