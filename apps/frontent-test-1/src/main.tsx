import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

import { App } from "@/App";
import { AuthProvider } from "@/auth/AuthProvider";
import { Toaster } from "@/components/ui/sonner";
import { ThemeProvider } from "@/theme/ThemeProvider";

import "./index.css";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
      staleTime: 15_000,
    },
  },
});

const rootElement = document.getElementById("root");
if (!rootElement) {
  throw new Error("缺少 #root 挂载节点");
}

createRoot(rootElement).render(
  <StrictMode>
    <ThemeProvider>
      <QueryClientProvider client={queryClient}>
        <AuthProvider>
          <App />
          <Toaster position="top-center" />
        </AuthProvider>
      </QueryClientProvider>
    </ThemeProvider>
  </StrictMode>,
);
