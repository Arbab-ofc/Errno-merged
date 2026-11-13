import { defineConfig } from 'vitest/config';
import { loadEnv } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const adminDirectory = path.dirname(fileURLToPath(import.meta.url));

export default defineConfig(({ mode }) => {
  // Keep existing component-local overrides while reading the shared root .env.
  for (const [key, value] of Object.entries(loadEnv(mode, adminDirectory, 'VITE_'))) {
    if (process.env[key] === undefined) process.env[key] = value;
  }
  return {
    envDir: path.resolve(adminDirectory, '..'),
    plugins: [react()],
    test: {
      environment: 'jsdom',
      setupFiles: './src/test/setup.js',
      restoreMocks: true,
    },
  };
});
