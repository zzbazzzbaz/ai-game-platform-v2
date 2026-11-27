import { useQuery } from "@tanstack/react-query";

import { renewSandbox } from "@/api/sessions";

/** 沙盒每次续期 5 分钟；每 2 分钟续一次，给失败留出重试余量。 */
const RENEW_INTERVAL_MS = 2 * 60 * 1000;

/**
 * 工作台打开期间轮询续期沙盒。
 *
 * 接口在没有沙盒或沙盒已失效时返回 renewed=false，不算错误；
 * 这里不重试、不弹 toast，避免干扰对话。
 */
export function useSandboxRenewal(threadId: string | null) {
  return useQuery({
    queryKey: ["sandbox-renewal", threadId],
    queryFn: () => renewSandbox(threadId as string),
    enabled: threadId !== null,
    refetchInterval: RENEW_INTERVAL_MS,
    refetchIntervalInBackground: true,
    refetchOnWindowFocus: true,
    retry: false,
    staleTime: 0,
    gcTime: 0,
  });
}
