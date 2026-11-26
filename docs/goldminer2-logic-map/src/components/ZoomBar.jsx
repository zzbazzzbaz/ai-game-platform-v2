import React from "react";
import { useReactFlow } from "@xyflow/react";
import { Maximize2, Minus, Plus } from "lucide-react";

export default function ZoomBar({ labels }) {
  const { zoomIn, zoomOut, fitView } = useReactFlow();

  return (
    <div className="zoom-bar">
      <button
        type="button"
        className="zoom-btn"
        aria-label={labels.zoomIn}
        title={labels.zoomIn}
        onClick={() => zoomIn({ duration: 180 })}
      >
        <Plus size={15} />
      </button>
      <button
        type="button"
        className="zoom-btn"
        aria-label={labels.zoomOut}
        title={labels.zoomOut}
        onClick={() => zoomOut({ duration: 180 })}
      >
        <Minus size={15} />
      </button>
      <button
        type="button"
        className="zoom-btn zoom-fit"
        aria-label={labels.fit}
        title={labels.fit}
        onClick={() => fitView({ padding: "6%", duration: 280 })}
      >
        <Maximize2 size={14} />
      </button>
    </div>
  );
}
