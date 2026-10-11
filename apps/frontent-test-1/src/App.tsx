import { createBrowserRouter, RouterProvider } from "react-router";

import { RequireAuth } from "@/auth/RequireAuth";
import { LoginPage } from "@/features/auth/LoginPage";
import { GamesPage } from "@/features/games/GamesPage";
import { WorkbenchPage } from "@/features/workbench/WorkbenchPage";
import { AppLayout } from "@/routes/AppLayout";
import { NotFoundPage } from "@/routes/NotFoundPage";

const router = createBrowserRouter([
  { path: "/login", element: <LoginPage /> },
  {
    element: (
      <RequireAuth>
        <AppLayout />
      </RequireAuth>
    ),
    children: [
      { path: "/", element: <GamesPage /> },
      { path: "/games/:gameId", element: <WorkbenchPage /> },
      { path: "/games/:gameId/threads/:threadId", element: <WorkbenchPage /> },
      { path: "*", element: <NotFoundPage /> },
    ],
  },
]);

export function App() {
  return <RouterProvider router={router} />;
}
