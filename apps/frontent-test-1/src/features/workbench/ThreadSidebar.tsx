import * as React from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { MessagesSquare, Plus } from "lucide-react";
import { useNavigate } from "react-router";
import { toast } from "sonner";

import { ApiError } from "@/api/client";
import { createThread, listThreads } from "@/api/games";
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
import { Skeleton } from "@/components/ui/skeleton";
import { formatDateTime } from "@/lib/format";
import { cn } from "@/lib/utils";

export function ThreadSidebar({
  gameId,
  activeThreadId,
}: {
  gameId: string;
  activeThreadId: string;
}) {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [dialogOpen, setDialogOpen] = React.useState(false);
  const [title, setTitle] = React.useState("");

  const { data: threads = [], isPending } = useQuery({
    queryKey: ["threads", gameId],
    queryFn: () => listThreads(gameId),
  });

  const createMutation = useMutation({
    mutationFn: (threadTitle: string) => createThread(gameId, threadTitle),
    onSuccess: (thread) => {
      void queryClient.invalidateQueries({ queryKey: ["threads", gameId] });
      setDialogOpen(false);
      setTitle("");
      navigate(`/games/${gameId}/threads/${thread.thread_id}`);
    },
    onError: (error) => {
      toast.error(error instanceof ApiError ? error.message : "创建会话失败，请重试");
    },
  });

  return (
    <aside className="bg-muted/20 flex w-64 shrink-0 flex-col border-r">
      <div className="flex items-center justify-between gap-2 border-b p-3">
        <span className="text-sm font-medium">会话</span>
        <Button
          variant="ghost"
          size="icon"
          aria-label="新建会话"
          onClick={() => setDialogOpen(true)}
        >
          <Plus />
        </Button>
      </div>

      <div className="scrollbar-thin min-h-0 flex-1 overflow-y-auto p-2">
        {isPending ? (
          <div className="flex flex-col gap-2">
            {Array.from({ length: 3 }).map((_, index) => (
              <Skeleton key={index} className="h-14 w-full" />
            ))}
          </div>
        ) : (
          <div className="flex flex-col gap-1">
            {threads.map((thread) => (
              <button
                key={thread.thread_id}
                type="button"
                onClick={() => navigate(`/games/${gameId}/threads/${thread.thread_id}`)}
                className={cn(
                  "hover:bg-accent flex flex-col items-start gap-1 rounded-md px-3 py-2 text-left transition-colors",
                  thread.thread_id === activeThreadId && "bg-accent",
                )}
              >
                <span className="flex w-full items-center gap-2">
                  <MessagesSquare className="text-muted-foreground size-3.5 shrink-0" />
                  <span className="truncate text-sm">{thread.title || "未命名会话"}</span>
                </span>
                <span className="text-muted-foreground text-[0.6875rem]">
                  {formatDateTime(thread.updated_at ?? thread.created_at)}
                </span>
              </button>
            ))}
          </div>
        )}
      </div>

      <Dialog
        open={dialogOpen}
        onOpenChange={(next) => {
          if (createMutation.isPending) return;
          setDialogOpen(next);
        }}
      >
        <DialogContent className="sm:max-w-sm">
          <DialogHeader>
            <DialogTitle>新建会话</DialogTitle>
            <DialogDescription>
              新会话会复用同一个工作区与数据库，适合换一个玩法重新开始。
            </DialogDescription>
          </DialogHeader>
          <div className="flex flex-col gap-2">
            <Label htmlFor="thread-title">会话名称</Label>
            <Input
              id="thread-title"
              value={title}
              onChange={(event) => setTitle(event.target.value)}
              placeholder="留空则使用「新会话」"
              maxLength={64}
              autoFocus
            />
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDialogOpen(false)}>
              取消
            </Button>
            <Button
              onClick={() => createMutation.mutate(title.trim() || "新会话")}
              disabled={createMutation.isPending}
            >
              创建
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </aside>
  );
}
