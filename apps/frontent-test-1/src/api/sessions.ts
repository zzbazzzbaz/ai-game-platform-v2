/** 预览接口（内部会触发沙盒 ensure，仅在用户主动加载时调用）。 */

import { apiFetch } from "./client";

export interface PreviewResponse {
  thread_id: string;
  novnc_url: string;
}

export function getPreviewUrl(threadId: string): Promise<PreviewResponse> {
  return apiFetch<PreviewResponse>(`/sessions/${threadId}/preview`);
}
