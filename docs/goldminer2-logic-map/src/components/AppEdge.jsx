import React from "react";
import { EdgeLabelRenderer, getSmoothStepPath } from "@xyflow/react";

export default function AppEdge({
  id,
  sourceX,
  sourceY,
  targetX,
  targetY,
  sourcePosition,
  targetPosition,
  markerEnd,
  label,
  selected,
  data,
}) {
  const side = data?.side;
  let path;
  let labelX;
  let labelY;

  if (side === "left" || side === "right") {
    const laneX =
      data?.at ??
      (side === "right" ? Math.max(sourceX, targetX) + 80 : Math.min(sourceX, targetX) - 80);
    path = `M ${sourceX},${sourceY} C ${laneX},${sourceY} ${laneX},${targetY} ${targetX},${targetY}`;
    labelX = 0.125 * (sourceX + targetX) + 0.75 * laneX;
    labelY = (sourceY + targetY) / 2;
  } else if (side === "top" || side === "bottom") {
    const laneY =
      data?.at ??
      (side === "bottom" ? Math.max(sourceY, targetY) + 80 : Math.min(sourceY, targetY) - 80);
    path = `M ${sourceX},${sourceY} C ${sourceX},${laneY} ${targetX},${laneY} ${targetX},${targetY}`;
    labelX = (sourceX + targetX) / 2;
    labelY = 0.125 * (sourceY + targetY) + 0.75 * laneY;
  } else {
    [path, labelX, labelY] = getSmoothStepPath({
      sourceX,
      sourceY,
      sourcePosition,
      targetX,
      targetY,
      targetPosition,
      borderRadius: 14,
      offset: 18,
    });
  }

  const kind = data?.kind ?? "flow";

  return (
    <>
      <path d={path} className="edge-hit" />
      <path
        id={id}
        d={path}
        className={`edge-path edge-${kind} ${selected ? "is-selected" : ""}`}
        markerEnd={markerEnd}
      />
      {label && (
        <EdgeLabelRenderer>
          <div
            className="edge-label"
            style={{
              transform: `translate(-50%, -50%) translate(${labelX}px, ${labelY}px)`,
            }}
          >
            {label}
          </div>
        </EdgeLabelRenderer>
      )}
    </>
  );
}
