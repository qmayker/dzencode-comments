import vue from "@vitejs/plugin-vue";
import { fileURLToPath } from "node:url";
import { defineConfig } from "vite";

const distDir = fileURLToPath(
  new URL("../comments/commenting/static/commenting/dist", import.meta.url),
);

export default defineConfig(({ command }) => ({
  plugins: [vue()],
  // The build is served by Django's static files; the dev server is mounted at the root.
  base: command === "build" ? "/static/commenting/dist/" : "/",
  server: {
    host: "127.0.0.1",
    port: 5173,
    strictPort: true,
    cors: true,
  },
  build: {
    outDir: distDir,
    emptyOutDir: true,
    manifest: true,
    rollupOptions: {
      input: "src/main.js",
    },
  },
}));
