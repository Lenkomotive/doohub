"use client";

import { Handle, Position, type NodeProps } from "@xyflow/react";
import { GitFork } from "lucide-react";

export function ConditionNode({ data, selected }: NodeProps) {
  const name = (data.name as string) || String(data.id);
  const field = (data.condition_field as string) || "?";
  const branches = (data.branches as Record<string, string>) || {};
  const branchKeys = Object.keys(branches);

  return (
    <div
      className={`w-44 rotate-0 rounded-lg border bg-card/90 px-3 py-2 shadow-sm ${
        selected ? "border-amber-500 ring-1 ring-amber-500/30" : "border-border/50"
      }`}
      style={{ clipPath: "polygon(50% 0%, 100% 50%, 50% 100%, 0% 50%)", minHeight: "5rem" }}
    >
      <Handle type="target" position={Position.Top} className="!bg-amber-500" />
      <div className="flex flex-col items-center justify-center text-center py-2">
        <GitFork className="h-3.5 w-3.5 text-amber-500 mb-0.5" />
        <span className="text-[10px] font-medium">{name}</span>
        <span className="text-[9px] text-muted-foreground">{field}</span>
      </div>
      <Handle type="source" position={Position.Bottom} className="!bg-amber-500" />
    </div>
  );
}
