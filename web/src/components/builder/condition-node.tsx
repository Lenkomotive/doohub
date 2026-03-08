"use client";

import { Handle, Position, type NodeProps } from "@xyflow/react";
import { GitFork } from "lucide-react";

export function ConditionNode({ data, selected }: NodeProps) {
  const name = (data.name as string) || String(data.id);
  const field = (data.condition_field as string) || "?";
  const branches = (data.branches as Record<string, string>) || {};
  const branchCount = Object.keys(branches).length;

  return (
    <div
      className={`w-44 rounded-lg border bg-amber-500/5 px-3 py-2 shadow-sm ${
        selected ? "border-emerald-500 ring-1 ring-emerald-500/30" : "border-amber-500/30"
      }`}
    >
      <Handle type="target" position={Position.Top} className="!bg-amber-500" />
      <div className="flex flex-col items-center justify-center text-center py-1">
        <GitFork className="h-3.5 w-3.5 text-amber-500 mb-0.5" />
        <span className="text-[10px] font-medium">{name}</span>
        <span className="text-[9px] text-muted-foreground">{field}</span>
        {branchCount > 0 && (
          <span className="text-[9px] text-muted-foreground mt-0.5">
            {branchCount} branch{branchCount !== 1 ? "es" : ""}
          </span>
        )}
      </div>
      <Handle type="source" position={Position.Bottom} className="!bg-amber-500" isConnectable />
    </div>
  );
}
