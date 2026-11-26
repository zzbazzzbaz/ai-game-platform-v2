import React from "react";

import { NodeHandles } from "./NodeHandles";

const STAT_TYPES = new Set(["stone", "gold", "diamond", "star", "save"]);

export default function GameNode({ data, selected }) {
  const value = STAT_TYPES.has(data.typeClass) ? data.attributes?.[0] : null;
  return (
    <div
      className={`game-node type-${data.typeClass} ${selected ? "is-selected" : ""}`}
    >
      <NodeHandles />
      <div className="node-strip" />
      <div className="node-body">
        <div className="node-title">{data.title}</div>
        {value && <span className="node-tag">{value}</span>}
      </div>
    </div>
  );
}
