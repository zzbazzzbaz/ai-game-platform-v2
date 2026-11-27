/** 预览接口（内部会触发沙盒 ensure，仅在用户主动加载时调用）。 */

import { apiFetch } from "./client";

export interface PreviewResponse {
  thread_id: string;
  novnc_url: string;
}

export interface RenewSandboxResponse {
  thread_id: string;
  sandbox_id: string | null;
  renewed: boolean;
  timeout_seconds: number;
}

export function getPreviewUrl(threadId: string): Promise<PreviewResponse> {
  return apiFetch<PreviewResponse>(`/sessions/${threadId}/preview`);
}

/** 续期当前会话的沙盒；没有沙盒或沙盒已失效时 renewed=false。 */
export function renewSandbox(threadId: string): Promise<RenewSandboxResponse> {
  return apiFetch<RenewSandboxResponse>(`/sessions/${threadId}/sandbox/renew`, {
    method: "POST",
  });
}
