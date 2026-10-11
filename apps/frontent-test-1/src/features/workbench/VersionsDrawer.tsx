import { useQuery } from "@tanstack/react-query";
import { ExternalLink, History, LoaderCircle, RefreshCw, Rocket } from "lucide-react";

import { listVersions, type VersionResponse } from "@/api/games";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Skeleton } from "@/components/ui/skeleton";
import { formatDateTime } from "@/lib/format";

const STATUS_META: Record<
  string,
  { label: string; variant: "success" | "warning" | "destructive" | "secondary" }
> = {
  deployed: { label: "已上线", variant: "success" },
  deploying: { label: "发布中", variant: "warning" },
  failed: { label: "发布失败", variant: "destructive" },
};

function VersionItem({ version, current }: { version: VersionResponse; current: boolean }) {
  const meta = STATUS_META[version.status] ?? { label: version.status, variant: "secondary" as const };

  return (
    <div className="flex flex-col gap-1 rounded-lg border p-3">
      <div className="flex items-center gap-2">
        <span className="font-mono text-sm font-medium">v{version.seq}</span>
        <Badge variant={meta.variant}>{meta.label}</Badge>
        {current && <Badge variant="outline">当前在线</Badge>}
      </div>
      {version.note && <p className="text-muted-foreground truncate text-xs">{version.note}</p>}
      <p className="text-muted-foreground text-xs">
        发布于 {formatDateTime(version.deployed_at ?? version.created_at)}
      </p>
      {version.revision && (
        <p className="text-muted-foreground truncate font-mono text-[0.6875rem]">
          revision {version.revision}
        </p>
      )}
    </div>
  );
}

/** 版本抽屉：展示发布历史与当前在线版本。 */
export function VersionsDrawer({
  gameId,
  publicUrl,
  open,
  onOpenChange,
}: {
  gameId: string;
  publicUrl: string | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const { data, isPending, isError, error, refetch, isRefetching } = useQuery({
    queryKey: ["versions", gameId],
    queryFn: () => listVersions(gameId),
    enabled: open,
  });

  const versions = data ?? [];
  const currentVersionId = versions.find((version) => version.status === "deployed")?.version_id;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent
        showCloseButton
        className="data-[state=open]:slide-in-from-right data-[state=closed]:slide-out-to-right top-0 right-0 left-auto h-full max-h-full w-full translate-x-0 translate-y-0 gap-4 overflow-y-auto rounded-none border-l p-5 sm:max-w-md"
      >
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <History className="size-4" />
            版本历史
          </DialogTitle>
          <DialogDescription>
            每次发布生成一个不可变版本；在对话里对 AI 说「发布」即可发布新版本
          </DialogDescription>
        </DialogHeader>

        <div className="flex items-center gap-2">
          {publicUrl !== null && (
            <Button asChild size="sm" variant="outline" className="flex-1">
              <a href={publicUrl} target="_blank" rel="noreferrer">
                <ExternalLink />
                打开游戏
              </a>
            </Button>
          )}
          <Button
            size="sm"
            variant="ghost"
            onClick={() => void refetch()}
            disabled={isRefetching}
            aria-label="刷新版本列表"
          >
            <RefreshCw className={isRefetching ? "animate-spin" : undefined} />
            刷新
          </Button>
        </div>

        {isPending ? (
          <div className="flex flex-col gap-2">
            {Array.from({ length: 2 }).map((_, index) => (
              <Skeleton key={index} className="h-20 w-full" />
            ))}
          </div>
        ) : isError ? (
          <p className="text-destructive text-sm">{error.message}</p>
        ) : versions.length === 0 ? (
          <div className="text-muted-foreground flex flex-col items-center gap-3 rounded-lg border border-dashed p-8 text-center text-sm">
            <LoaderCircle className="size-5 opacity-0" />
            <Rocket className="size-5" />
            <div>
              <p className="text-foreground font-medium">还没有发布过</p>
              <p className="mt-1">在对话里对 AI 说「发布」，即可生成公网可玩的链接</p>
            </div>
          </div>
        ) : (
          <div className="flex flex-col gap-2">
            {versions.map((version) => (
              <VersionItem
                key={version.version_id}
                version={version}
                current={version.version_id === currentVersionId}
              />
            ))}
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}
