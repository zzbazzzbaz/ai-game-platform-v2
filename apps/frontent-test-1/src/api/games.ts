/** 游戏 / 会话 / 版本接口。 */

import { apiFetch } from "./client";

export interface GameResponse {
  game_id: string;
  name: string;
  status: string;
  sandbox_id: string | null;
  public_url: string | null;
  created_at: string;
  updated_at?: string;
}

export interface ThreadResponse {
  thread_id: string;
  game_id: string;
  title: string;
  status: string;
  created_at: string;
  updated_at?: string;
}

export interface VersionResponse {
  version_id: string;
  seq: number;
  status: string;
  note: string;
  revision: string | null;
  created_at: string;
  deployed_at: string | null;
}

export function listGames(): Promise<GameResponse[]> {
  return apiFetch<GameResponse[]>("/games");
}

export function createGame(name: string): Promise<GameResponse> {
  return apiFetch<GameResponse>("/games", { method: "POST", body: { name } });
}

export function getGame(gameId: string): Promise<GameResponse> {
  return apiFetch<GameResponse>(`/games/${gameId}`);
}

export function listThreads(gameId: string): Promise<ThreadResponse[]> {
  return apiFetch<ThreadResponse[]>(`/games/${gameId}/threads`);
}

export function createThread(gameId: string, title: string): Promise<ThreadResponse> {
  return apiFetch<ThreadResponse>(`/games/${gameId}/threads`, {
    method: "POST",
    body: { title },
  });
}

export function listVersions(gameId: string): Promise<VersionResponse[]> {
  return apiFetch<VersionResponse[]>(`/games/${gameId}/versions`);
}
