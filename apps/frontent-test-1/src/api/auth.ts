/** 认证接口（注册 / 登录）。 */

import { apiFetch } from "./client";

export interface AuthResponse {
  user_id: string;
  username: string;
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

export function register(username: string, password: string): Promise<AuthResponse> {
  return apiFetch<AuthResponse>("/auth/register", {
    method: "POST",
    body: { username, password },
    auth: false,
  });
}

export function login(username: string, password: string): Promise<AuthResponse> {
  return apiFetch<AuthResponse>("/auth/login", {
    method: "POST",
    body: { username, password },
    auth: false,
  });
}
