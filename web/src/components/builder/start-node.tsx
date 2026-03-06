"use client";

import { Handle, Position } from "@xyflow/react";
import { Play } from "lucide-react";

export function StartNode() {
  return (
    <div className="flex h-12 w-12 items-center justify-center rounded-full border-2 border-green-500 bg-green-500/10">
      <Play className="h-5 w-5 text-green-500" />
      <Handle type="source" position={Position.Bottom} className="!bg-green-500" />
    </div>
  );
}
