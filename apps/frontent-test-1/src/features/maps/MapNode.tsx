import { Handle, Position, type Node, type NodeProps } from "@xyflow/react";

import { cn } from "@/lib/utils";
import type { MapNodeData } from "@/features/maps/layout";

const KIND_STYLES: Record<string, string> = {
  start: "border-primary/50 bg-primary/5",
  action: "",
  decision: "border-dashed border-primary/50",
  reward: "border-emerald-500/40 bg-emerald-500/5",
  penalty: "border-destructive/40 bg-destructive/5",
  end: "bg-muted/60",
  note: "border-dashed bg-muted/30",
  value: "border-primary/30 bg-secondary/60",
  level: "border-primary/30 bg-secondary/60",
};

/** 玩法图节点：无图标，只显示标题和必要的数值。 */
export function MapNode({ data, selected }: NodeProps<Node<MapNodeData>>) {
  return (
    <div
      className={cn(
        "bg-card w-[168px] rounded-lg border px-3 py-2 text-center shadow-sm",
        KIND_STYLES[data.kind] ?? KIND_STYLES.action,
        selected && "ring-ring ring-offset-background ring-2 ring-offset-2",
      )}
    >
      <Handle type="target" position={Position.Left} />
      <Handle
        id="loop-target"
        type="target"
        position={Position.Top}
        className="opacity-0"
      />
      <p className="truncate text-sm font-medium">{data.title}</p>
      {data.value && (
        <p className="text-muted-foreground mt-0.5 truncate text-xs">{data.value}</p>
      )}
      {data.value2 && <p className="text-muted-foreground truncate text-xs">{data.value2}</p>}
      <Handle type="source" position={Position.Right} />
      <Handle
        id="loop-source"
        type="source"
        position={Position.Top}
        className="opacity-0"
      />
    </div>
  );
}
