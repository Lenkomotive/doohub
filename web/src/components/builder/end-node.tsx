"use client";

import { Handle, Position } from "@xyflow/react";
import { Square } from "lucide-react";

export function EndNode() {
  return (
    <div className="flex h-12 w-12 items-center justify-center rounded-full border-2 border-muted-foreground bg-muted/30">
      <Handle type="target" position={Position.Top} className="!bg-muted-foreground" />
      <Square className="h-4 w-4 text-muted-foreground" />
      <span className="absolute -bottom-5 text-[10px] text-muted-foreground">Done</span>
    </div>
  );
}
