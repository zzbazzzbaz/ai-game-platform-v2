import * as React from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  ArrowLeft,
  Copy,
  ExternalLink,
  History,
  LoaderCircle,
  MonitorPlay,
  Rocket,
} from "lucide-react";
import { Link, useLocation, useNavigate, useParams } from "react-router";
import { toast } from "sonner";

import { ApiError } from "@/api/client";
import { createDemo, createThread, getGame, listThreads, publishGame } from "@/api/games";
import { ensureLangGraphThread } from "@/api/langgraph";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { ChatPanel } from "@/features/chat/ChatPanel";
import { PreviewPanel } from "@/features/workbench/PreviewPanel";
import { ThreadSidebar } from "@/features/workbench/ThreadSidebar";
import { useVersions } from "@/features/workbench/useVersions";
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
  const location = useLocation();
  const queryClient = useQueryClient();

  const [previewOpen, setPreviewOpen] = React.useState(false);
  const [versionsOpen, setVersionsOpen] = React.useState(false);
  const [demoDialogOpen, setDemoDialogOpen] = React.useState(false);
  const autoCreateRef = React.useRef(false);

  // 由「生成体验版」带过来的提示词：只在本次跳转的会话里自动发送一次。
  const kickoffPrompt =
    (location.state as { kickoffPrompt?: string } | null)?.kickoffPrompt ?? null;

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

  const versionsQuery = useVersions(gameId);

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

  const publishMutation = useMutation({
    mutationFn: () => publishGame(gameId, { thread_id: threadIdParam }),
    onSuccess: (result) => {
      toast.success(`已开始发布 v${result.seq}`);
      void queryClient.invalidateQueries({ queryKey: ["versions", gameId] });
    },
    onError: (error) => {
      toast.error(error instanceof ApiError ? error.message : "发布失败，请重试");
      // 409 表示已有发布在途：刷新版本列表，让按钮进入「发布中」。
      void queryClient.invalidateQueries({ queryKey: ["versions", gameId] });
    },
  });

  const createDemoMutation = useMutation({
    mutationFn: () => createDemo(gameId),
    onSuccess: (result) => {
      // 路由参数变化时 WorkbenchPage 会被复用，必须显式关掉旧页面的弹窗。
      setDemoDialogOpen(false);
      toast.success("体验版项目已创建，正在自动改造");
      navigate(`/games/${result.game_id}/threads/${result.thread_id}`, {
        state: { kickoffPrompt: result.kickoff_prompt },
      });
    },
    onError: (error) => {
      toast.error(error instanceof ApiError ? error.message : "创建体验版失败，请重试");
    },
  });

  // 首次发布成功后 /games/{id} 的 public_url 才会写入，轮询到 deployed 时刷新一次。
  const hasDeployedVersion =
    versionsQuery.data?.some((version) => version.status === "deployed") ?? false;
  const publicUrl = gameQuery.data?.public_url ?? null;
  React.useEffect(() => {
    if (hasDeployedVersion && publicUrl === null) {
      void queryClient.invalidateQueries({ queryKey: ["game", gameId] });
    }
  }, [hasDeployedVersion, publicUrl, gameId, queryClient]);

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
  const published = publicUrl !== null;
  const deploying =
    versionsQuery.data?.some((version) => version.status === "deploying") ?? false;

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
        {deploying ? (
          <Badge variant="warning">发布中</Badge>
        ) : (
          published && <Badge variant="success">已发布</Badge>
        )}

        <div className="ml-auto flex items-center gap-1">
          {publicUrl !== null && (
            <Button asChild variant="outline" size="sm">
              <a href={publicUrl} target="_blank" rel="noreferrer">
                <ExternalLink />
                打开游戏
              </a>
            </Button>
          )}
          <Button
            variant="outline"
            size="sm"
            onClick={() => setDemoDialogOpen(true)}
            disabled={gameQuery.isPending || createDemoMutation.isPending}
          >
            {createDemoMutation.isPending ? (
              <LoaderCircle className="animate-spin" />
            ) : (
              <Copy />
            )}
            生成体验版
          </Button>
          <Button
            size="sm"
            onClick={() => publishMutation.mutate()}
            disabled={deploying || publishMutation.isPending || gameQuery.isPending}
          >
            {deploying || publishMutation.isPending ? (
              <LoaderCircle className="animate-spin" />
            ) : (
              <Rocket />
            )}
            {deploying ? "发布中" : "发布"}
          </Button>
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
                initialPrompt={kickoffPrompt}
                onInitialPromptConsumed={() =>
                  navigate(location.pathname, { replace: true, state: null })
                }
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

      <Dialog
        open={demoDialogOpen}
        onOpenChange={(open) => {
          if (!createDemoMutation.isPending) setDemoDialogOpen(open);
        }}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>生成体验版</DialogTitle>
            <DialogDescription>
              将复制当前项目的代码和素材，创建一个独立的体验版项目（含新数据库）。
              进入新项目后会自动开始改造：只保留第一关，并加上「玩完整版」入口。
              建议等当前生成结束后再操作；复制和改造可能产生额外资源费用。
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setDemoDialogOpen(false)}
              disabled={createDemoMutation.isPending}
            >
              取消
            </Button>
            <Button
              onClick={() => createDemoMutation.mutate()}
              disabled={createDemoMutation.isPending}
            >
              {createDemoMutation.isPending ? (
                <LoaderCircle className="animate-spin" />
              ) : (
                <Copy />
              )}
              {createDemoMutation.isPending ? "正在复制…" : "创建并开始改造"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
