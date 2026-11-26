import React from "react";
import {
  Background,
  BackgroundVariant,
  MarkerType,
  ReactFlow,
} from "@xyflow/react";
import {
  Info,
  Layers,
  Repeat2,
  Target,
  Workflow,
} from "lucide-react";

import AppEdge from "./components/AppEdge";
import DetailPanel from "./components/DetailPanel";
import GameNode from "./components/GameNode";
import LevelNode from "./components/LevelNode";
import SpacerNode from "./components/SpacerNode";
import ZoomBar from "./components/ZoomBar";
import loop from "./data/loop.json";
import states from "./data/states.json";
import hook from "./data/hook.json";
import levels from "./data/levels.json";
import { LAYOUT } from "./layout";
import { UI_CONFIG } from "./ui";

const VIEWS = [loop, states, hook, levels];
const { meta: META, ui: UI, legend: LEGEND, viewIcons: VIEW_ICONS } = UI_CONFIG;

const NODE_TYPES = {
  game: GameNode,
  level: LevelNode,
  spacer: SpacerNode,
};

const EDGE_TYPES = {
  app: AppEdge,
};

const TAB_ICONS = {
  repeat: Repeat2,
  workflow: Workflow,
  target: Target,
  layers: Layers,
};

const EDGE_COLORS = {
  flow: "#7c8ba1",
  branch: "#0284c7",
  loop: "#6366f1",
  success: "#059669",
  muted: "#cbd5e1",
};

const ROUTE_HANDLES = {
  bottom: { source: "bottom-out", target: "bottom-in" },
  top: { source: "top-out", target: "top-in" },
  right: { source: "out", target: "right-in" },
  left: { source: "left-out", target: "left-in" },
};

function inferHandles(from, to) {
  if (!from || !to) return { source: "out", target: "in" };
  const dx = to[0] - from[0];
  const dy = to[1] - from[1];
  if (Math.abs(dy) >= Math.abs(dx)) {
    return dy > 0
      ? { source: "bottom-out", target: "top-in" }
      : { source: "top-out", target: "bottom-in" };
  }
  return dx > 0
    ? { source: "out", target: "in" }
    : { source: "left-out", target: "right-in" };
}

function buildNodes(view) {
  const layout = LAYOUT[view.id];
  const nodes = view.nodes.map((node, index) => {
    const typeClass = layout.types?.[node.id] ?? "action";
    const [x, y] = layout.positions[node.id] ?? [0, 0];
    return {
      id: node.id,
      type: typeClass === "level" ? "level" : "game",
      position: { x, y },
      data: { ...node, typeClass, index },
    };
  });
  if (layout.bounds) {
    nodes.push({
      id: "__spacer",
      type: "spacer",
      position: { x: layout.bounds[0], y: layout.bounds[1] },
      data: {},
      selectable: false,
      draggable: false,
    });
  }
  return nodes;
}

function buildEdges(view) {
  const layout = LAYOUT[view.id];
  const positions = layout.positions;
  const routes = layout.routes ?? {};
  const nodeTypes = layout.types ?? {};

  return view.edges.map((edge, index) => {
    const route = routes[`${edge.from}->${edge.to}`]?.side;
    const at = routes[`${edge.from}->${edge.to}`]?.at;
    const handles = route
      ? ROUTE_HANDLES[route] ?? ROUTE_HANDLES.bottom
      : inferHandles(positions[edge.from], positions[edge.to]);

    let kind = "flow";
    if (route) {
      kind = "loop";
    } else if (nodeTypes[edge.to] === "end") {
      kind = "success";
    } else if (nodeTypes[edge.from] === "level" && nodeTypes[edge.to] === "level") {
      kind = "success";
    } else if (nodeTypes[edge.from] === "decision") {
      kind = "branch";
    } else if (nodeTypes[edge.to] === "save") {
      kind = "muted";
    }

    return {
      id: `e-${index}`,
      source: edge.from,
      target: edge.to,
      label: edge.title,
      type: "app",
      sourceHandle: handles.source,
      targetHandle: handles.target,
      markerEnd: {
        type: MarkerType.ArrowClosed,
        color: EDGE_COLORS[kind] ?? EDGE_COLORS.flow,
        width: 17,
        height: 17,
      },
      data: { side: route, at, kind, content: edge },
    };
  });
}

export default function App() {
  const [active, setActive] = React.useState(VIEWS[0].id);
  const [selection, setSelection] = React.useState(null);
  const [panelOpen, setPanelOpen] = React.useState(false);
  const view = VIEWS.find((item) => item.id === active) ?? VIEWS[0];
  const nodes = React.useMemo(() => buildNodes(view), [view]);
  const edges = React.useMemo(() => buildEdges(view), [view]);
  const fitTimer = React.useRef(null);

  React.useEffect(() => {
    document.title = `${META.title} · ${META.product}`;
  }, []);

  React.useEffect(() => {
    setSelection(null);
    setPanelOpen(false);
  }, [active]);

  React.useEffect(() => () => window.clearTimeout(fitTimer.current), []);

  const onNodeClick = React.useCallback((_, node) => {
    if (node.type === "spacer") return;
    setSelection({ kind: "node", node });
    setPanelOpen(true);
  }, []);

  const onEdgeClick = React.useCallback((_, edge) => {
    setSelection({ kind: "edge", edge });
    setPanelOpen(true);
  }, []);

  const closePanel = React.useCallback(() => {
    setSelection(null);
    setPanelOpen(false);
  }, []);

  const handleInit = React.useCallback((instance) => {
    window.clearTimeout(fitTimer.current);
    fitTimer.current = window.setTimeout(() => {
      instance.fitView({ padding: "6%", duration: 320 });
    }, 350);
  }, []);

  return (
    <div className="app">
      <nav className="tabs">
        <div className="tabs-inner">
          {VIEWS.map((item) => {
            const Icon = TAB_ICONS[VIEW_ICONS[item.id]] ?? Repeat2;
            return (
              <button
                key={item.id}
                className={`tab ${active === item.id ? "is-active" : ""}`}
                onClick={() => setActive(item.id)}
                type="button"
              >
                <Icon size={14} strokeWidth={2.1} />
                {item.tab}
              </button>
            );
          })}
        </div>
      </nav>

      <main className="workspace">
        <section className="canvas-card">
          <div className="flow-wrap">
            <ReactFlow
              key={active}
              nodes={nodes}
              edges={edges}
              nodeTypes={NODE_TYPES}
              edgeTypes={EDGE_TYPES}
              fitView
              fitViewOptions={{ padding: "6%" }}
              minZoom={0.3}
              maxZoom={1.7}
              nodesConnectable={false}
              onInit={handleInit}
              onNodeClick={onNodeClick}
              onEdgeClick={onEdgeClick}
              onPaneClick={closePanel}
              proOptions={{ hideAttribution: true }}
            >
              <Background
                variant={BackgroundVariant.Dots}
                gap={18}
                size={1.1}
                color="#cbd5e1"
              />
              <ZoomBar labels={UI} />
            </ReactFlow>

            <div className="canvas-tools">
              <span className="canvas-hint">{UI.hint}</span>
              <button
                className="icon-btn info-btn"
                onClick={() => {
                  setSelection(null);
                  setPanelOpen(true);
                }}
                aria-label={UI.info}
                title={UI.info}
                type="button"
              >
                <Info size={15} />
              </button>
            </div>
          </div>
        </section>

        <DetailPanel
          selection={selection}
          view={view}
          open={panelOpen}
          onClose={closePanel}
          ui={UI}
          legend={LEGEND}
        />
      </main>
    </div>
  );
}
