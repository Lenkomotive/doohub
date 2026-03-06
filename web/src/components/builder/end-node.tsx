"use client";

import { Handle, Position, type NodeProps } from "@xyflow/react";
import { Square } from "lucide-react";

export function EndNode({ data }: NodeProps) {
  const status = (data.status as string) || "done";
  const isFail = status === "failed";

  return (
    <div
      className={`flex h-12 w-12 items-center justify-center rounded-full border-2 ${
        isFail
          ? "border-red-500 bg-red-500/10"
          : "border-muted-foreground bg-muted/30"
      }`}
    >
      <Handle type="target" position={Position.Top} className={isFail ? "!bg-red-500" : "!bg-muted-foreground"} />
      <Square className={`h-4 w-4 ${isFail ? "text-red-500" : "text-muted-foreground"}`} />
      <span className="absolute -bottom-5 text-[10px] text-muted-foreground">
        {data.name as string || status}
      </span>
    </div>
  );
}
