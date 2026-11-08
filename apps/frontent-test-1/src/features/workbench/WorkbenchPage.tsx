import * as React from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, ExternalLink, History, LoaderCircle, MonitorPlay } from "lucide-react";
import { Link, useNavigate, useParams } from "react-router";

import { ApiError } from "@/api/client";
import { createThread, getGame, listThreads } from "@/api/games";
import { ensureLangGraphThread } from "@/api/langgraph";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ChatPanel } from "@/features/chat/ChatPanel";
import { PreviewPanel } from "@/features/workbench/PreviewPanel";
import { ThreadSidebar } from "@/features/workbench/ThreadSidebar";
import { VersionsDrawer } from "@/features/workbench/VersionsDrawer";
import { Skeleton } from "@/components/ui/skeleton";

const SUGGESTIONS = [
  "做一个贪吃蛇游戏，有分数和排行榜",
  "做一个打砖块游戏，有音效和关卡",
  "做一个 2048 小游戏，支持触屏滑动",
  "做一个双人对战的小游戏",
];

export function WorkbenchPage() {
  const { gameId = "", threadId: threadIdParam } = useParams<{
    gameId: string;
    threadId?: string;
  }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const [previewOpen, setPreviewOpen] = React.useState(false);
  const [versionsOpen, setVersionsOpen] = React.useState(false);
  const autoCreateRef = React.useRef(false);

  const gameQuery = useQuery({
    queryKey: ["game", gameId],
    queryFn: () => getGame(gameId),
    enabled: gameId !== "",
  });

  const threadsQuery = useQuery({
    queryKey: ["threads", gameId],
    queryFn: () => listThreads(gameId),
    enabled: gameId !== "",
  });

  // 平台会话与 LangGraph 线程一一对应：进入工作台先补建运行时线程（幂等），
  // 否则读取历史会 404（平台会话先于运行时线程存在）。
  const threadReadyQuery = useQuery({
    queryKey: ["langgraph-thread", threadIdParam],
    queryFn: async () => {
      await ensureLangGraphThread(threadIdParam as string);
      return true;
    },
    enabled: threadIdParam !== undefined,
    staleTime: Number.POSITIVE_INFINITY,
    retry: 1,
  });

  const createThreadMutation = useMutation({
    mutationFn: () => createThread(gameId, "初始会话"),
    onSuccess: (thread) => {
      void queryClient.invalidateQueries({ queryKey: ["threads", gameId] });
      navigate(`/games/${gameId}/threads/${thread.thread_id}`, { replace: true });
    },
    onError: () => {
      autoCreateRef.current = false;
    },
  });

  const { mutate: createThreadMutate } = createThreadMutation;

  // 未指定会话时：跳到最近会话，没有则自动建一个
  React.useEffect(() => {
    if (threadIdParam !== undefined || gameId === "") return;
    const threads = threadsQuery.data;
    if (!threads) return;

    if (threads.length > 0) {
      navigate(`/games/${gameId}/threads/${threads[0].thread_id}`, { replace: true });
      return;
    }
    if (!autoCreateRef.current) {
      autoCreateRef.current = true;
      createThreadMutate();
    }
  }, [threadIdParam, threadsQuery.data, gameId, navigate, createThreadMutate]);

  const game = gameQuery.data;
  const publicUrl = game?.public_url ?? null;
  const published = publicUrl !== null;

  const threadId = threadIdParam ?? null;
  const preparingThread = threadId === null && !threadsQuery.isError;

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <header className="flex items-center gap-2 border-b px-3 py-2">
        <Button asChild variant="ghost" size="icon" aria-label="返回游戏列表">
          <Link to="/">
            <ArrowLeft />
          </Link>
        </Button>
        {gameQuery.isPending ? (
          <Skeleton className="h-5 w-40" />
        ) : (
          <span className="truncate text-sm font-medium">{game?.name ?? "游戏"}</span>
        )}
        {published && <Badge variant="success">已发布</Badge>}

        <div className="ml-auto flex items-center gap-1">
          {publicUrl !== null && (
            <Button asChild variant="outline" size="sm">
              <a href={publicUrl} target="_blank" rel="noreferrer">
                <ExternalLink />
                打开游戏
              </a>
            </Button>
          )}
          <Button variant="outline" size="sm" onClick={() => setVersionsOpen(true)}>
            <History />
            版本
          </Button>
          <Button
            variant={previewOpen ? "default" : "outline"}
            size="sm"
            onClick={() => setPreviewOpen((open) => !open)}
            disabled={threadId === null}
          >
            <MonitorPlay />
            预览
          </Button>
        </div>
      </header>

      {gameQuery.isError ? (
        <div className="flex flex-1 flex-col items-center justify-center gap-3 p-6 text-center">
          <p className="text-destructive text-sm">{gameQuery.error.message}</p>
          <Button variant="outline" onClick={() => void gameQuery.refetch()}>
            重试
          </Button>
        </div>
      ) : threadsQuery.isError ? (
        <div className="flex flex-1 flex-col items-center justify-center gap-3 p-6 text-center">
          <p className="text-destructive text-sm">{threadsQuery.error.message}</p>
          <Button variant="outline" onClick={() => void threadsQuery.refetch()}>
            重试
          </Button>
        </div>
      ) : (
        <div className="relative flex min-h-0 flex-1">
          {threadId !== null && (
            <ThreadSidebar gameId={gameId} activeThreadId={threadId} />
          )}

          {threadId !== null ? (
            threadReadyQuery.isSuccess ? (
              <ChatPanel
                key={threadId}
                gameId={gameId}
                threadId={threadId}
                suggestions={SUGGESTIONS}
              />
            ) : threadReadyQuery.isError ? (
              <div className="flex flex-1 flex-col items-center justify-center gap-3 p-6 text-center">
                <p className="text-destructive text-sm">
                  {threadReadyQuery.error instanceof Error
                    ? threadReadyQuery.error.message
                    : "对话线程初始化失败"}
                </p>
                <Button variant="outline" size="sm" onClick={() => void threadReadyQuery.refetch()}>
                  重试
                </Button>
              </div>
            ) : (
              <div className="text-muted-foreground flex flex-1 items-center justify-center gap-2 text-sm">
                <LoaderCircle className="size-4 animate-spin" />
                正在准备对话…
              </div>
            )
          ) : preparingThread ? (
            <div className="text-muted-foreground flex flex-1 flex-col items-center justify-center gap-3 text-sm">
              <LoaderCircle className="size-5 animate-spin" />
              {createThreadMutation.isError ? (
                <div className="flex flex-col items-center gap-2">
                  <p className="text-destructive">
                    {createThreadMutation.error instanceof ApiError
                      ? createThreadMutation.error.message
                      : "创建会话失败"}
                  </p>
                  <Button variant="outline" size="sm" onClick={() => createThreadMutate()}>
                    重试
                  </Button>
                </div>
              ) : (
                <p>正在准备会话…</p>
              )}
            </div>
          ) : null}

          {previewOpen && threadId !== null && (
            <PreviewPanel threadId={threadId} onClose={() => setPreviewOpen(false)} />
          )}
        </div>
      )}

      <VersionsDrawer
        gameId={gameId}
        publicUrl={publicUrl}
        open={versionsOpen}
        onOpenChange={setVersionsOpen}
      />
    </div>
  );
}
