"use client";

import { Handle, Position, type NodeProps } from "@xyflow/react";
import { Layers } from "lucide-react";
import { Badge } from "@/components/ui/badge";

export function TemplateNode({ data, selected }: NodeProps) {
  const name = (data.name as string) || String(data.id);
  const templateName = (data.template_name as string) || "No template selected";

  return (
    <div
      className={`w-52 rounded-lg border-2 bg-card/90 px-3 py-2 shadow-sm ${
        selected ? "border-emerald-500 ring-1 ring-emerald-500/30" : "border-border/50"
      }`}
    >
      <Handle type="target" position={Position.Top} className="!bg-primary" />
      <div className="flex items-center gap-1.5 mb-1">
        <Layers className="h-3.5 w-3.5 text-indigo-500" />
        <span className="text-xs font-medium truncate">{name}</span>
      </div>
      <Badge variant="outline" className="text-[9px] px-1 py-0">
        {templateName}
      </Badge>
      <Handle type="source" position={Position.Bottom} className="!bg-primary" />
    </div>
  );
}
