import * as React from "react";
import { LoaderCircle, Plus } from "lucide-react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "react-router";
import { toast } from "sonner";

import { createGame } from "@/api/games";
import { ApiError } from "@/api/client";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

function errorMessage(error: unknown): string {
  if (error instanceof ApiError) return error.message;
  if (error instanceof TypeError) return "无法连接服务器，请确认服务已启动";
  return "创建失败，请稍后重试";
}

export function NewGameDialog({
  open,
  onOpenChange,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const [name, setName] = React.useState("");
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const mutation = useMutation({
    mutationFn: (gameName: string) => createGame(gameName),
    onSuccess: (game) => {
      void queryClient.invalidateQueries({ queryKey: ["games"] });
      toast.success("游戏已创建");
      onOpenChange(false);
      setName("");
      navigate(`/games/${game.game_id}`);
    },
    onError: (error) => {
      toast.error(errorMessage(error));
    },
  });

  const handleSubmit = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (mutation.isPending) return;
    mutation.mutate(name.trim());
  };

  return (
    <Dialog
      open={open}
      onOpenChange={(next) => {
        if (mutation.isPending) return;
        onOpenChange(next);
      }}
    >
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>新建游戏</DialogTitle>
          <DialogDescription>
            创建后会初始化该游戏的工作区与数据库，然后进入对话开始生成。
          </DialogDescription>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          <div className="flex flex-col gap-2">
            <Label htmlFor="game-name">游戏名称</Label>
            <Input
              id="game-name"
              value={name}
              onChange={(event) => setName(event.target.value)}
              placeholder="留空则使用「未命名游戏」"
              maxLength={64}
              autoFocus
              disabled={mutation.isPending}
            />
          </div>
          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={() => onOpenChange(false)}
              disabled={mutation.isPending}
            >
              取消
            </Button>
            <Button type="submit" disabled={mutation.isPending}>
              {mutation.isPending && <LoaderCircle className="animate-spin" />}
              <Plus />
              创建
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
