/** LangGraph Server 对接：运行时线程补建 + 带登录态的 SDK Client。 */

import { Client } from "@langchain/langgraph-sdk";

import { env } from "@/lib/env";

import { authedFetch } from "./client";
import { getSession } from "./tokens";

/** SDK 需要绝对地址：把相对基路径（/lg）解析成当前源下的绝对地址。 */
export function langGraphBaseUrl(): string {
  return new URL(env.lgBaseUrl, window.location.origin).toString().replace(/\/$/, "");
}

/** 供 LangGraph SDK 使用：每次请求注入最新 access token（401 自动续期一次）。 */
export const langGraphFetch: typeof fetch = (input, init) => authedFetch(input, init);

/**
 * 构造 SDK Client：用 `onRequest` 在每次请求时注入最新 access token
 * （token 会随续期变化，不能固定在 defaultHeaders 里）。
 */
export function createLangGraphClient(): Client {
  return new Client({
    apiUrl: langGraphBaseUrl(),
    apiKey: null,
    onRequest: (_url, init) => {
      const token = getSession()?.accessToken;
      if (!token) return init;
      const headers = new Headers(init.headers);
      headers.set("Authorization", `Bearer ${token}`);
      return { ...init, headers };
    },
  });
}

/**
 * 用平台 thread_id 补建运行时线程（幂等）。
 *
 * 平台会话由 api 创建（agent 的 ensure 依赖 thread_id → game_id 映射），
 * 前端拿到 thread_id 后在 LangGraph 侧用同一 UUID 建线程，保证两侧一致。
 */
export async function ensureLangGraphThread(threadId: string): Promise<void> {
  const response = await authedFetch(`${langGraphBaseUrl()}/threads`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ thread_id: threadId, if_exists: "do_nothing" }),
  });
  if (!response.ok) {
    throw new Error(`创建对话线程失败（HTTP ${response.status}）`);
  }
}
