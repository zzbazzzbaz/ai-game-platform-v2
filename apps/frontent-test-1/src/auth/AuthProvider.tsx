import * as React from "react";

import * as authApi from "@/api/auth";
import { onUnauthorized } from "@/api/client";
import { clearSession, getSession, setSession, type AuthSession } from "@/api/tokens";

interface AuthContextValue {
  session: AuthSession | null;
  login: (username: string, password: string) => Promise<void>;
  register: (username: string, password: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = React.createContext<AuthContextValue | null>(null);

function toSession(response: authApi.AuthResponse): AuthSession {
  return {
    userId: response.user_id,
    username: response.username,
    accessToken: response.access_token,
    refreshToken: response.refresh_token,
  };
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [session, setSessionState] = React.useState<AuthSession | null>(() => getSession());

  React.useEffect(() => {
    // token 续期失败（会话失效）时自动登出
    return onUnauthorized(() => setSessionState(null));
  }, []);

  const login = React.useCallback(async (username: string, password: string) => {
    const response = await authApi.login(username, password);
    const next = toSession(response);
    setSession(next);
    setSessionState(next);
  }, []);

  const register = React.useCallback(async (username: string, password: string) => {
    const response = await authApi.register(username, password);
    const next = toSession(response);
    setSession(next);
    setSessionState(next);
  }, []);

  const logout = React.useCallback(() => {
    clearSession();
    setSessionState(null);
  }, []);

  const value = React.useMemo(
    () => ({ session, login, register, logout }),
    [session, login, register, logout],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const context = React.useContext(AuthContext);
  if (context === null) {
    throw new Error("useAuth 必须在 AuthProvider 内使用");
  }
  return context;
}
