import React from "react";
import { Handle, Position } from "@xyflow/react";

const hidden = { opacity: 0 };

export function NodeHandles() {
  return (
    <>
      <Handle type="target" position={Position.Left} id="in" style={hidden} />
      <Handle type="source" position={Position.Right} id="out" style={hidden} />
      <Handle type="target" position={Position.Right} id="right-in" style={hidden} />
      <Handle type="source" position={Position.Left} id="left-out" style={hidden} />
      <Handle type="target" position={Position.Top} id="top-in" style={hidden} />
      <Handle type="source" position={Position.Top} id="top-out" style={hidden} />
      <Handle type="target" position={Position.Bottom} id="bottom-in" style={hidden} />
      <Handle type="source" position={Position.Bottom} id="bottom-out" style={hidden} />
    </>
  );
}
