/** 玩法图接口：列表只返回 id，详情按 id 单独读取。 */

import { apiFetch } from "./client";

export interface GameMapNode {
  id: string;
  title: string;
  detail: string;
  attributes: string[];
  kind: string;
}

export interface GameMapEdge {
  from: string;
  to: string;
  title: string;
  detail: string;
  attributes: string[];
  kind: string;
}

export interface GameMapDetail {
  game_id: string;
  map_id: string;
  title: string;
  revision: number;
  nodes: GameMapNode[];
  edges: GameMapEdge[];
  created_at: string;
  updated_at: string;
}

export function listGameMaps(gameId: string): Promise<string[]> {
  return apiFetch<string[]>(`/games/${gameId}/maps`);
}

export function getGameMap(gameId: string, mapId: string): Promise<GameMapDetail> {
  return apiFetch<GameMapDetail>(
    `/games/${gameId}/maps/${encodeURIComponent(mapId)}`,
  );
}
