import type { ReactNode } from "react";
import { Navigate, useLocation } from "react-router";

import { useAuth } from "@/auth/AuthProvider";

/** 登录守卫：未登录跳登录页，登录后回到原地址。 */
export function RequireAuth({ children }: { children: ReactNode }) {
  const { session } = useAuth();
  const location = useLocation();

  if (session === null) {
    return (
      <Navigate
        to="/login"
        replace
        state={{ from: location.pathname + location.search }}
      />
    );
  }

  return <>{children}</>;
}
