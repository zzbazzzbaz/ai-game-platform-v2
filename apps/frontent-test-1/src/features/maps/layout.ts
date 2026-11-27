/** 玩法图自动布局：按连线层级排布，不依赖具体游戏的节点 id 或坐标。 */

import { MarkerType, type Edge, type Node } from "@xyflow/react";

import type { GameMapDetail, GameMapEdge } from "@/api/maps";

export interface MapNodeData extends Record<string, unknown> {
  title: string;
  value?: string;
  value2?: string;
  kind: string;
}

export interface MapEdgeData extends Record<string, unknown> {
  index: number;
}

const NODE_WIDTH = 168;
const NODE_HEIGHT = 44;
const GAP_X = 112;
const GAP_Y = 56;

export function layoutGameMap(detail: GameMapDetail): {
  nodes: Node<MapNodeData>[];
  edges: Edge<MapEdgeData>[];
} {
  const ids = detail.nodes.map((node) => node.id);
  const layers = assignLayers(ids, detail.edges);

  const rows = new Map<number, string[]>();
  for (const id of ids) {
    const layer = layers.get(id) ?? 0;
    const row = rows.get(layer);
    if (row) {
      row.push(id);
    } else {
      rows.set(layer, [id]);
    }
  }

  const nodes = detail.nodes.map((node) => {
    const layer = layers.get(node.id) ?? 0;
    const row = rows.get(layer) ?? [node.id];
    const column = row.indexOf(node.id);
    const columnHeight = row.length * NODE_HEIGHT + (row.length - 1) * GAP_Y;
    const y = column * (NODE_HEIGHT + GAP_Y) - columnHeight / 2 + NODE_HEIGHT / 2;
    return {
      id: node.id,
      type: "mapNode",
      position: { x: layer * (NODE_WIDTH + GAP_X), y },
      data: {
        title: node.title,
        value:
          node.kind === "value" || node.kind === "level" ? node.attributes[0] : undefined,
        value2: node.kind === "level" ? node.attributes[1] : undefined,
        kind: node.kind,
      },
    } satisfies Node<MapNodeData>;
  });

  const edges = detail.edges.map((edge, index) => {
    const color =
      edge.kind === "failure"
        ? "var(--destructive)"
        : edge.kind === "success"
          ? "var(--primary)"
          : "var(--muted-foreground)";
    const sourceLayer = layers.get(edge.from) ?? 0;
    const targetLayer = layers.get(edge.to) ?? 0;
    const backwards = targetLayer <= sourceLayer;
    return {
      id: `edge-${index}`,
      source: edge.from,
      target: edge.to,
      type: "smoothstep",
      sourceHandle: backwards ? "loop-source" : undefined,
      targetHandle: backwards ? "loop-target" : undefined,
      label: edge.title || undefined,
      animated: edge.kind === "loop",
      data: { index },
      style: {
        stroke: color,
        strokeWidth: 1.5,
        strokeDasharray: edge.kind === "loop" ? "6 4" : undefined,
      },
      labelStyle: { fill: "var(--foreground)", fontSize: 11 },
      labelBgStyle: { fill: "var(--background)", fillOpacity: 0.92 },
      labelBgPadding: [6, 2],
      labelBgBorderRadius: 4,
      markerEnd: { type: MarkerType.ArrowClosed, color, width: 14, height: 14 },
    } satisfies Edge<MapEdgeData>;
  });

  return { nodes, edges };
}

function assignLayers(ids: string[], edges: GameMapEdge[]): Map<string, number> {
  const known = new Set(ids);
  const outgoing = new Map<string, string[]>();
  const indegree = new Map<string, number>();
  for (const id of ids) {
    outgoing.set(id, []);
    indegree.set(id, 0);
  }
  for (const edge of edges) {
    if (!known.has(edge.from) || !known.has(edge.to) || edge.from === edge.to) continue;
    outgoing.get(edge.from)?.push(edge.to);
    indegree.set(edge.to, (indegree.get(edge.to) ?? 0) + 1);
  }

  const layers = new Map<string, number>();
  const queue = ids.filter((id) => (indegree.get(id) ?? 0) === 0);
  if (queue.length === 0 && ids.length > 0) queue.push(ids[0]);
  for (const id of queue) layers.set(id, 0);

  let cursor = 0;
  while (cursor < queue.length) {
    const id = queue[cursor];
    cursor += 1;
    const layer = layers.get(id) ?? 0;
    for (const next of outgoing.get(id) ?? []) {
      if (layers.has(next)) continue;
      layers.set(next, layer + 1);
      queue.push(next);
    }
  }

  let maxLayer = -1;
  for (const layer of layers.values()) maxLayer = Math.max(maxLayer, layer);
  const fallback = maxLayer + 1;
  for (const id of ids) {
    if (!layers.has(id)) layers.set(id, fallback);
  }
  return layers;
}
