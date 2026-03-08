"use client";

import { Handle, Position, type NodeProps } from "@xyflow/react";
import { Layers } from "lucide-react";

export function TemplateNode({ data, selected }: NodeProps) {
  const name = (data.name as string) || String(data.id);
  const templateId = data.template_id as string | undefined;

  return (
    <div
      className={`w-44 rounded-lg border bg-violet-500/5 px-3 py-2 shadow-sm ${
        selected ? "border-emerald-500 ring-1 ring-emerald-500/30" : "border-violet-500/30"
      }`}
    >
      <Handle type="target" position={Position.Top} className="!bg-violet-500" />
      <div className="flex flex-col items-center justify-center text-center py-1">
        <Layers className="h-3.5 w-3.5 text-violet-500 mb-0.5" />
        <span className="text-[10px] font-medium">{name}</span>
        {templateId ? (
          <span className="text-[9px] text-muted-foreground">template #{templateId}</span>
        ) : (
          <span className="text-[9px] text-red-400">no template</span>
        )}
      </div>
      <Handle type="source" position={Position.Bottom} className="!bg-violet-500" isConnectable />
    </div>
  );
}
