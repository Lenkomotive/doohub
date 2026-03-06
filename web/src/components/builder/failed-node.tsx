"use client";

import { Handle, Position, type NodeProps } from "@xyflow/react";
import { Square } from "lucide-react";

export function FailedNode({ data }: NodeProps) {
  return (
    <div className="flex h-12 w-12 items-center justify-center rounded-full border-2 border-red-500 bg-red-500/10">
      <Handle type="target" position={Position.Top} className="!bg-red-500" />
      <Square className="h-4 w-4 text-red-500" />
      <Handle type="source" position={Position.Bottom} className="!bg-red-500" />
      <span className="absolute -bottom-5 text-[10px] text-red-400">Failed</span>
    </div>
  );
}
