import * as React from "react";
import { useMutation } from "@tanstack/react-query";
import {
  ExternalLink,
  LoaderCircle,
  Maximize2,
  Minimize2,
  MonitorPlay,
  RefreshCw,
  X,
} from "lucide-react";

import { ApiError } from "@/api/client";
import { getPreviewUrl } from "@/api/sessions";
import { Button } from "@/components/ui/button";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { cn } from "@/lib/utils";

type ScaleMode = "scale" | "off";

function withScaleMode(url: string, mode: ScaleMode): string {
  return url.replace(/resize=[a-z]+/, `resize=${mode}`);
}

/** 预览面板：点击才加载（preview 接口会触发沙盒 ensure，可能较慢）。 */
export function PreviewPanel({ threadId, onClose }: { threadId: string; onClose: () => void }) {
  const containerRef = React.useRef<HTMLDivElement>(null);
  const [url, setUrl] = React.useState<string | null>(null);
  const [scaleMode, setScaleMode] = React.useState<ScaleMode>("scale");
  const [fullscreen, setFullscreen] = React.useState(false);

  const mutation = useMutation({
    mutationFn: () => getPreviewUrl(threadId),
    onSuccess: (data) => setUrl(data.novnc_url),
    onError: (error) => {
      if (error instanceof ApiError) {
        // 错误详情直接展示在面板内
      }
    },
  });

  React.useEffect(() => {
    const onChange = () => setFullscreen(document.fullscreenElement === containerRef.current);
    document.addEventListener("fullscreenchange", onChange);
    return () => document.removeEventListener("fullscreenchange", onChange);
  }, []);

  const toggleFullscreen = () => {
    const element = containerRef.current;
    if (!element) return;
    if (document.fullscreenElement === element) {
      void document.exitFullscreen();
    } else {
      void element.requestFullscreen();
    }
  };

  const errorMessage =
    mutation.error instanceof ApiError
      ? mutation.error.message
      : mutation.error
        ? "预览加载失败，请稍后重试"
        : null;

  return (
    <div
      ref={containerRef}
      className={cn(
        "bg-background flex flex-col border-l",
        fullscreen
          ? "h-full w-full"
          : "absolute inset-0 z-20 lg:static lg:z-auto lg:h-full lg:w-[46%] lg:min-w-[26rem]",
      )}
    >
      <div className="flex items-center gap-1 border-b p-2">
        <span className="px-1 text-sm font-medium">预览</span>
        {url !== null && (
          <>
            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  variant="ghost"
                  size="icon"
                  aria-label="刷新预览地址"
                  onClick={() => mutation.mutate()}
                  disabled={mutation.isPending}
                >
                  <RefreshCw className={cn(mutation.isPending && "animate-spin")} />
                </Button>
              </TooltipTrigger>
              <TooltipContent>重新获取预览地址</TooltipContent>
            </Tooltip>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setScaleMode((mode) => (mode === "scale" ? "off" : "scale"))}
            >
              {scaleMode === "scale" ? "适应窗口" : "原始比例"}
            </Button>
          </>
        )}
        <div className="ml-auto flex items-center gap-1">
          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                variant="ghost"
                size="icon"
                aria-label={fullscreen ? "退出全屏" : "全屏"}
                onClick={toggleFullscreen}
              >
                {fullscreen ? <Minimize2 /> : <Maximize2 />}
              </Button>
            </TooltipTrigger>
            <TooltipContent>{fullscreen ? "退出全屏" : "全屏"}</TooltipContent>
          </Tooltip>
          <Tooltip>
            <TooltipTrigger asChild>
              <Button variant="ghost" size="icon" aria-label="关闭预览" onClick={onClose}>
                <X />
              </Button>
            </TooltipTrigger>
            <TooltipContent>关闭预览</TooltipContent>
          </Tooltip>
        </div>
      </div>

      <div className="relative min-h-0 flex-1">
        {url === null ? (
          <div className="flex h-full flex-col items-center justify-center gap-4 p-6 text-center">
            <span className="bg-muted flex size-12 items-center justify-center rounded-full">
              {mutation.isPending ? (
                <LoaderCircle className="size-5 animate-spin" />
              ) : (
                <MonitorPlay className="size-5" />
              )}
            </span>
            {mutation.isPending ? (
              <div className="text-muted-foreground flex flex-col gap-1 text-sm">
                <p className="text-foreground font-medium">正在准备预览环境…</p>
                <p>启动沙盒并拉起游戏服务，首次可能需要 1–3 分钟</p>
              </div>
            ) : errorMessage !== null ? (
              <div className="flex flex-col items-center gap-3">
                <p className="text-destructive text-sm">{errorMessage}</p>
                <Button variant="outline" size="sm" onClick={() => mutation.mutate()}>
                  <RefreshCw />
                  重试
                </Button>
              </div>
            ) : (
              <div className="flex flex-col items-center gap-3">
                <div className="text-muted-foreground flex flex-col gap-1 text-sm">
                  <p className="text-foreground font-medium">在这里试玩你的游戏</p>
                  <p>点击加载后，会在沙盒里运行游戏并同步画面</p>
                </div>
                <Button onClick={() => mutation.mutate()}>
                  <MonitorPlay />
                  加载预览
                </Button>
              </div>
            )}
            <p className="text-muted-foreground max-w-xs text-xs">
              沙盒空闲一段时间后会被暂停，画面可能断开，点刷新即可重新获取地址
            </p>
          </div>
        ) : (
          <>
            <iframe
              key={url}
              title="游戏预览"
              src={withScaleMode(url, scaleMode)}
              className="h-full w-full border-0 bg-white"
              allow="clipboard-read; clipboard-write"
            />
            <a
              href={url}
              target="_blank"
              rel="noreferrer"
              className="bg-background/80 text-muted-foreground hover:text-foreground absolute right-2 bottom-2 flex items-center gap-1 rounded-md border px-2 py-1 text-xs backdrop-blur"
            >
              <ExternalLink className="size-3" />
              新窗口打开
            </a>
          </>
        )}
      </div>
    </div>
  );
}
