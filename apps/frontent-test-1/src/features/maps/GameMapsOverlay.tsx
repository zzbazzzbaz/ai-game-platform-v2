import * as React from "react";
import { useQueries, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Background,
  Controls,
  ReactFlow,
  type Edge,
  type Node,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { LoaderCircle, RefreshCw, Sparkles, Workflow, X } from "lucide-react";

import {
  getGameMap,
  listGameMaps,
  type GameMapDetail,
  type GameMapEdge,
  type GameMapNode,
} from "@/api/maps";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { MapNode } from "@/features/maps/MapNode";
import { layoutGameMap } from "@/features/maps/layout";
import {
  edgeReferencePrompt,
  GENERATE_MAPS_PROMPT,
  nodeReferencePrompt,
  UPDATE_MAPS_PROMPT,
} from "@/features/maps/prompts";
import { formatDateTime } from "@/lib/format";
import { cn } from "@/lib/utils";
import { useTheme } from "@/theme/ThemeProvider";

export interface GameMapsOverlayProps {
  gameId: string;
  open: boolean;
  canUseAgent: boolean;
  isGenerating: boolean;
  onClose: () => void;
  onSendPrompt: (prompt: string) => void;
  onFillPrompt: (prompt: string) => void;
}

type Selection =
  | { mapId: string; type: "node"; id: string }
  | { mapId: string; type: "edge"; index: number }
  | null;

const NODE_TYPES = { mapNode: MapNode };

function errorText(error: unknown): string {
  if (error instanceof Error && error.message) return error.message;
  return "加载玩法图失败";
}

/** 全屏玩法图浮层：只读展示，写入通过对话交给 Agent。 */
export function GameMapsOverlay(props: GameMapsOverlayProps) {
  if (!props.open) return null;
  return <GameMapsOverlayContent {...props} />;
}

function GameMapsOverlayContent({
  gameId,
  canUseAgent,
  isGenerating,
  onClose,
  onSendPrompt,
  onFillPrompt,
}: GameMapsOverlayProps) {
  const queryClient = useQueryClient();
  const [explicitMapId, setExplicitMapId] = React.useState<string | null>(null);
  const [selection, setSelection] = React.useState<Selection>(null);
  const [refreshing, setRefreshing] = React.useState(false);

  const listQuery = useQuery({
    queryKey: ["game-maps", gameId],
    queryFn: () => listGameMaps(gameId),
    staleTime: 0,
    retry: 1,
  });
  const mapIds = listQuery.data;
  const ids = React.useMemo(() => mapIds ?? [], [mapIds]);

  const detailQueries = useQueries({
    queries: ids.map((mapId) => ({
      queryKey: ["game-map", gameId, mapId],
      queryFn: () => getGameMap(gameId, mapId),
      staleTime: 0,
      retry: 1,
    })),
  });

  const details = React.useMemo(() => {
    const map = new Map<string, GameMapDetail>();
    detailQueries.forEach((query, index) => {
      const mapId = ids[index];
      if (query.data && mapId) map.set(mapId, query.data);
    });
    return map;
  }, [detailQueries, ids]);

  // 列表刷新后若原选中图已不存在，自动回落到第一张。
  const selectedMapId =
    explicitMapId !== null && ids.includes(explicitMapId)
      ? explicitMapId
      : (ids[0] ?? null);

  React.useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [onClose]);

  const selectedIndex = selectedMapId === null ? -1 : ids.indexOf(selectedMapId);
  const selectedQuery = selectedIndex >= 0 ? detailQueries[selectedIndex] : undefined;
  const detail = selectedQuery?.data;

  const selectMap = (mapId: string) => {
    setExplicitMapId(mapId);
    setSelection(null);
    const index = ids.indexOf(mapId);
    const query = detailQueries[index];
    if (query?.isError) void query.refetch();
  };

  const handleRefresh = async () => {
    if (refreshing) return;
    setRefreshing(true);
    try {
      await listQuery.refetch();
      await queryClient.invalidateQueries({ queryKey: ["game-map", gameId] });
    } finally {
      setRefreshing(false);
    }
  };

  const send = (prompt: string) => {
    if (!canUseAgent || isGenerating) return;
    onSendPrompt(prompt);
  };

  const disabledHint = !canUseAgent
    ? "请先进入一个会话"
    : isGenerating
      ? "正在生成，完成后再更新"
      : null;

  return (
    <div className="bg-background fixed inset-0 z-50 flex flex-col">
      <header className="flex flex-wrap items-center gap-2 border-b px-4 py-2">
        <Workflow className="size-4" />
        <span className="text-sm font-medium">玩法图</span>
        <div className="ml-auto flex items-center gap-2">
          {disabledHint !== null && (
            <span className="text-muted-foreground text-xs">{disabledHint}</span>
          )}
          <Button
            variant="ghost"
            size="sm"
            onClick={() => void handleRefresh()}
            disabled={refreshing || listQuery.isPending}
          >
            <RefreshCw className={refreshing ? "animate-spin" : undefined} />
            刷新
          </Button>
          {ids.length > 0 && (
            <Button
              size="sm"
              onClick={() => send(UPDATE_MAPS_PROMPT)}
              disabled={!canUseAgent || isGenerating}
            >
              <Sparkles />
              更新玩法图
            </Button>
          )}
          <Button variant="ghost" size="icon" onClick={onClose} aria-label="关闭玩法图">
            <X />
          </Button>
        </div>
      </header>

      {ids.length > 0 && (
        <div className="flex items-center gap-2 overflow-x-auto border-b px-4 py-2">
          <div className="flex items-center gap-1">
            {ids.map((mapId) => {
              const active = mapId === selectedMapId;
              return (
                <button
                  key={mapId}
                  type="button"
                  onClick={() => selectMap(mapId)}
                  className={cn(
                    "rounded-full border px-3 py-1 text-sm whitespace-nowrap transition-colors",
                    active
                      ? "bg-primary text-primary-foreground border-transparent"
                      : "hover:bg-accent",
                  )}
                >
                  {details.get(mapId)?.title ?? mapId}
                </button>
              );
            })}
          </div>
          {detail !== undefined && (
            <span className="text-muted-foreground ml-auto shrink-0 text-xs">
              第 {detail.revision} 版 · 更新于 {formatDateTime(detail.updated_at)}
            </span>
          )}
        </div>
      )}

      <div className="flex min-h-0 flex-1 flex-col">
        {listQuery.isPending ? (
          <div className="text-muted-foreground flex flex-1 items-center justify-center gap-2 text-sm">
            <LoaderCircle className="size-4 animate-spin" />
            正在加载玩法图…
          </div>
        ) : listQuery.isError ? (
          <div className="flex flex-1 flex-col items-center justify-center gap-3 p-6 text-center">
            <p className="text-destructive text-sm">{errorText(listQuery.error)}</p>
            <Button variant="outline" size="sm" onClick={() => void listQuery.refetch()}>
              重试
            </Button>
          </div>
        ) : ids.length === 0 ? (
          <div className="flex flex-1 flex-col items-center justify-center gap-3 p-6 text-center">
            <Workflow className="text-muted-foreground size-8" />
            <p className="font-medium">还没有玩法图</p>
            <p className="text-muted-foreground max-w-md text-sm">
              玩法图由对话中的 AI 根据当前游戏代码生成；查看玩法图不会启动沙盒。
            </p>
            <Button
              onClick={() => send(GENERATE_MAPS_PROMPT)}
              disabled={!canUseAgent || isGenerating}
            >
              <Sparkles />
              生成玩法图
            </Button>
          </div>
        ) : selectedQuery?.isPending ? (
          <div className="flex flex-1 items-center justify-center">
            <Skeleton className="h-40 w-72" />
          </div>
        ) : selectedQuery?.isError ? (
          <div className="flex flex-1 flex-col items-center justify-center gap-3 p-6 text-center">
            <p className="text-destructive text-sm">{errorText(selectedQuery.error)}</p>
            <Button variant="outline" size="sm" onClick={() => void selectedQuery.refetch()}>
              重试
            </Button>
          </div>
        ) : detail !== undefined ? (
          <div className="flex min-h-0 flex-1">
            <MapCanvas
              detail={detail}
              onNodeClick={(id) =>
                setSelection({ mapId: detail.map_id, type: "node", id })
              }
              onEdgeClick={(index) =>
                setSelection({ mapId: detail.map_id, type: "edge", index })
              }
              onPaneClick={() => setSelection(null)}
            />
            {selection !== null && selection.mapId === detail.map_id && (
              <DetailPanel
                detail={detail}
                selection={selection}
                canUseAgent={canUseAgent}
                onClose={() => setSelection(null)}
                onFillPrompt={onFillPrompt}
              />
            )}
          </div>
        ) : null}
      </div>
    </div>
  );
}

function MapCanvas({
  detail,
  onNodeClick,
  onEdgeClick,
  onPaneClick,
}: {
  detail: GameMapDetail;
  onNodeClick: (id: string) => void;
  onEdgeClick: (index: number) => void;
  onPaneClick: () => void;
}) {
  const graph = React.useMemo(() => layoutGameMap(detail), [detail]);
  const { resolvedTheme } = useTheme();

  return (
    <div className="relative min-h-0 flex-1">
      <ReactFlow
        key={detail.map_id}
        nodes={graph.nodes}
        edges={graph.edges}
        nodeTypes={NODE_TYPES}
        forceColorMode={resolvedTheme}
        fitView
        minZoom={0.2}
        maxZoom={1.6}
        nodesDraggable={false}
        nodesConnectable={false}
        onNodeClick={(_, node: Node) => onNodeClick(node.id)}
        onEdgeClick={(_, edge: Edge) => {
          const index = edge.data?.index;
          if (typeof index === "number") onEdgeClick(index);
        }}
        onPaneClick={onPaneClick}
      >
        <Background gap={18} size={1} color="var(--border)" />
        <Controls showInteractive={false} />
      </ReactFlow>
      <p className="bg-background/85 text-muted-foreground pointer-events-none absolute top-3 right-3 rounded-md border px-2 py-1 text-xs">
        点方块或线看说明
      </p>
    </div>
  );
}

function DetailPanel({
  detail,
  selection,
  canUseAgent,
  onClose,
  onFillPrompt,
}: {
  detail: GameMapDetail;
  selection: Exclude<Selection, null>;
  canUseAgent: boolean;
  onClose: () => void;
  onFillPrompt: (prompt: string) => void;
}) {
  const node: GameMapNode | undefined =
    selection.type === "node"
      ? detail.nodes.find((item) => item.id === selection.id)
      : undefined;
  const edge: GameMapEdge | undefined =
    selection.type === "edge" ? detail.edges[selection.index] : undefined;
  const item = node ?? edge;
  if (!item) return null;

  const sourceTitle =
    edge === undefined
      ? ""
      : (detail.nodes.find((candidate) => candidate.id === edge.from)?.title ?? edge.from);
  const targetTitle =
    edge === undefined
      ? ""
      : (detail.nodes.find((candidate) => candidate.id === edge.to)?.title ?? edge.to);
  const description =
    edge === undefined ? node?.detail : edge.detail || `从 ${sourceTitle} 到 ${targetTitle}`;

  const referencePrompt =
    node !== undefined
      ? nodeReferencePrompt(detail, node)
      : edge !== undefined
        ? edgeReferencePrompt(detail, edge)
        : "";

  return (
    <aside className="bg-card flex w-80 shrink-0 flex-col overflow-y-auto border-l p-4">
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <Badge variant="secondary">{node !== undefined ? "节点" : "连线"}</Badge>
          <h3 className="mt-2 truncate text-sm font-medium">
            {item.title || (node !== undefined ? "未命名节点" : "未命名连线")}
          </h3>
        </div>
        <Button variant="ghost" size="icon" onClick={onClose} aria-label="关闭说明">
          <X />
        </Button>
      </div>
      <p className="text-muted-foreground mt-2 text-sm whitespace-pre-wrap">
        {description || "暂无说明"}
      </p>
      {item.attributes.length > 0 && (
        <ul className="mt-3 flex flex-col gap-1">
          {item.attributes.map((attribute, index) => (
            <li key={`${attribute}-${index}`} className="bg-muted rounded px-2 py-1 text-xs">
              {attribute}
            </li>
          ))}
        </ul>
      )}
      <Button
        className="mt-4 w-full"
        size="sm"
        onClick={() => onFillPrompt(referencePrompt)}
        disabled={!canUseAgent}
      >
        告诉 AI 改这里
      </Button>
    </aside>
  );
}
