import { useQuery } from "@tanstack/react-query";

import { listVersions } from "@/api/games";

/** 版本列表：有 deploying 版本时每 3 秒自动刷新，全部进入终态后停止。 */
export function useVersions(gameId: string) {
  return useQuery({
    queryKey: ["versions", gameId],
    queryFn: () => listVersions(gameId),
    enabled: gameId !== "",
    refetchInterval: (query) =>
      query.state.data?.some((version) => version.status === "deploying") ? 3000 : false,
  });
}
