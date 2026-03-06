"use client";

import { Handle, Position, type NodeProps } from "@xyflow/react";
import { Bot } from "lucide-react";
import { Badge } from "@/components/ui/badge";

export function AgentNode({ data, selected }: NodeProps) {
  const name = (data.name as string) || String(data.id);
  const model = (data.model as string) || "default";
  const prompt = (data.prompt_template as string) || "";
  const preview = prompt.length > 60 ? prompt.slice(0, 60) + "…" : prompt;

  return (
    <div
      className={`w-52 rounded-lg border bg-card/90 px-3 py-2 shadow-sm ${
        selected ? "border-primary ring-1 ring-primary/30" : "border-border/50"
      }`}
    >
      <Handle type="target" position={Position.Top} className="!bg-primary" />
      <div className="flex items-center gap-1.5 mb-1">
        <Bot className="h-3.5 w-3.5 text-primary" />
        <span className="text-xs font-medium truncate">{name}</span>
      </div>
      {preview && (
        <p className="text-[10px] leading-tight text-muted-foreground line-clamp-2 mb-1.5">
          {preview}
        </p>
      )}
      <Badge variant="outline" className="text-[9px] px-1 py-0">
        {model}
      </Badge>
      <Handle type="source" position={Position.Bottom} className="!bg-primary" />
    </div>
  );
}
