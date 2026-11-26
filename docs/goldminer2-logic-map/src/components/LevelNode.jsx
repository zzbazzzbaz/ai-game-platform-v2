import React from "react";

import { NodeHandles } from "./NodeHandles";

export default function LevelNode({ data, selected }) {
  const number = String((data.index ?? 0) + 1).padStart(2, "0");
  const target = data.attributes?.[0];
  const time = data.attributes?.[1]?.replace(/^限时\s*/, "");

  return (
    <div className={`level-node ${selected ? "is-selected" : ""}`}>
      <NodeHandles />
      <div className="level-top">
        <span className="level-number">{number}</span>
        <span className="level-time">{time}</span>
      </div>
      <div className="level-title">{data.title}</div>
      <div className="level-target">{target}</div>
    </div>
  );
}
