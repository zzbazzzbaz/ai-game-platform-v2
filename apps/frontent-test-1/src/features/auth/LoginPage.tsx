import * as React from "react";
import { Gamepad2, LoaderCircle } from "lucide-react";
import { Navigate, useLocation, useNavigate } from "react-router";
import { toast } from "sonner";

import { ApiError } from "@/api/client";
import { useAuth } from "@/auth/AuthProvider";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";

type Mode = "login" | "register";

function errorMessage(error: unknown): string {
  if (error instanceof ApiError) return error.message;
  if (error instanceof TypeError) return "无法连接服务器，请确认服务已启动";
  return "操作失败，请稍后重试";
}

export function LoginPage() {
  const { session, login, register } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const [mode, setMode] = React.useState<Mode>("login");
  const [username, setUsername] = React.useState("");
  const [password, setPassword] = React.useState("");
  const [confirmPassword, setConfirmPassword] = React.useState("");
  const [submitting, setSubmitting] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);

  const from = (location.state as { from?: string } | null)?.from ?? "/";

  if (session !== null) {
    return <Navigate to="/" replace />;
  }

  const switchMode = (next: Mode) => {
    setMode(next);
    setError(null);
    setConfirmPassword("");
  };

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (submitting) return;

    const name = username.trim();
    if (name.length < 3 || name.length > 64) {
      setError("用户名长度须为 3-64 个字符");
      return;
    }
    if (mode === "register" && password.length < 8) {
      setError("密码长度至少 8 位");
      return;
    }
    if (mode === "login" && password.length === 0) {
      setError("请输入密码");
      return;
    }
    if (mode === "register" && password !== confirmPassword) {
      setError("两次输入的密码不一致");
      return;
    }

    setSubmitting(true);
    setError(null);
    try {
      if (mode === "login") {
        await login(name, password);
        toast.success("登录成功");
      } else {
        await register(name, password);
        toast.success("注册成功，已自动登录");
      }
      navigate(from, { replace: true });
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="flex min-h-full items-center justify-center p-4">
      <Card className="w-full max-w-sm">
        <CardHeader className="gap-3">
          <div className="flex items-center gap-2">
            <span className="bg-primary text-primary-foreground flex size-9 items-center justify-center rounded-lg">
              <Gamepad2 className="size-5" />
            </span>
            <CardTitle className="text-xl">AI 游戏平台</CardTitle>
          </div>
          <CardDescription>与 AI 对话，生成、试玩并发布你的游戏</CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col gap-4">
          <Tabs value={mode} onValueChange={(value) => switchMode(value as Mode)}>
            <TabsList className="w-full">
              <TabsTrigger value="login">登录</TabsTrigger>
              <TabsTrigger value="register">注册</TabsTrigger>
            </TabsList>
          </Tabs>

          <form onSubmit={handleSubmit} className="flex flex-col gap-4">
            <div className="flex flex-col gap-2">
              <Label htmlFor="username">用户名</Label>
              <Input
                id="username"
                name="username"
                autoComplete="username"
                placeholder="3-64 个字符"
                value={username}
                onChange={(event) => setUsername(event.target.value)}
                disabled={submitting}
                required
              />
            </div>
            <div className="flex flex-col gap-2">
              <Label htmlFor="password">密码</Label>
              <Input
                id="password"
                name="password"
                type="password"
                autoComplete={mode === "login" ? "current-password" : "new-password"}
                placeholder={mode === "register" ? "至少 8 位" : "请输入密码"}
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                disabled={submitting}
                required
              />
            </div>
            {mode === "register" && (
              <div className="flex flex-col gap-2">
                <Label htmlFor="confirm-password">确认密码</Label>
                <Input
                  id="confirm-password"
                  name="confirm-password"
                  type="password"
                  autoComplete="new-password"
                  placeholder="再次输入密码"
                  value={confirmPassword}
                  onChange={(event) => setConfirmPassword(event.target.value)}
                  disabled={submitting}
                  required
                />
              </div>
            )}

            {error !== null && (
              <p className="text-destructive text-sm" role="alert">
                {error}
              </p>
            )}

            <Button type="submit" disabled={submitting} className="mt-1">
              {submitting && <LoaderCircle className="animate-spin" />}
              {mode === "login" ? "登录" : "注册并登录"}
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
