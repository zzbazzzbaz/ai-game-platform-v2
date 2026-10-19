import path from "node:path";

import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig, loadEnv, type ProxyOptions } from "vite";

/** 本地唯一配置源为 apps/.env（envDir 指到上一级目录），缺失即报错。 */
export default defineConfig(({ command, mode }) => {
  const envDir = path.resolve(import.meta.dirname, "..");
  const env = loadEnv(mode, envDir, "");

  // 代理目标只有 dev server 需要；生产构建由 Caddy/nginx 同源反代，镜像里没有 apps/.env
  const apiProxyTarget = env.VITE_API_PROXY_TARGET;
  const lgProxyTarget = env.VITE_LG_PROXY_TARGET;
  if (command === "serve" && (!apiProxyTarget || !lgProxyTarget)) {
    throw new Error("缺少 VITE_API_PROXY_TARGET / VITE_LG_PROXY_TARGET（配置源：apps/.env）");
  }

  const proxy: Record<string, string | ProxyOptions> =
    apiProxyTarget && lgProxyTarget
      ? {
          // 平台后端
          "/api": { target: apiProxyTarget, changeOrigin: true },
          // LangGraph Server（去掉 /lg 前缀）
          "/lg": {
            target: lgProxyTarget,
            changeOrigin: true,
            rewrite: (p) => p.replace(/^\/lg/, ""),
          },
        }
      : {};

  return {
    plugins: [react(), tailwindcss()],
    resolve: {
      alias: { "@": path.resolve(import.meta.dirname, "src") },
    },
    envDir,
    server: {
      port: 5173,
      strictPort: true,
      proxy,
    },
  };
});
