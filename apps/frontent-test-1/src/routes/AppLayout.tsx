import { Gamepad2, LogOut } from "lucide-react";
import { Link, Outlet, useNavigate } from "react-router";

import { useAuth } from "@/auth/AuthProvider";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { ThemeToggle } from "@/theme/ThemeToggle";

export function AppLayout() {
  const { session, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate("/login", { replace: true });
  };

  return (
    <div className="flex h-full flex-col">
      <header className="bg-background/80 sticky top-0 z-30 border-b backdrop-blur">
        <div className="flex h-14 items-center gap-3 px-4">
          <Link to="/" className="flex items-center gap-2">
            <span className="bg-primary text-primary-foreground flex size-7 items-center justify-center rounded-md">
              <Gamepad2 className="size-4" />
            </span>
            <span className="text-sm font-semibold">AI 游戏平台</span>
          </Link>

          <div className="ml-auto flex items-center gap-1">
            <ThemeToggle />
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="ghost" size="sm" className="gap-2">
                  <span className="bg-muted flex size-6 items-center justify-center rounded-full text-xs">
                    {session?.username.slice(0, 1).toUpperCase()}
                  </span>
                  <span className="max-w-32 truncate">{session?.username}</span>
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="w-44">
                <DropdownMenuLabel className="text-muted-foreground text-xs font-normal">
                  已登录
                </DropdownMenuLabel>
                <DropdownMenuItem
                  variant="destructive"
                  onSelect={handleLogout}
                >
                  <LogOut />
                  退出登录
                </DropdownMenuItem>
                <DropdownMenuSeparator />
                <DropdownMenuLabel className="text-muted-foreground text-xs font-normal">
                  {session?.userId}
                </DropdownMenuLabel>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        </div>
      </header>

      <main className="flex min-h-0 flex-1 flex-col">
        <Outlet />
      </main>
    </div>
  );
}
