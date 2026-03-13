"use client";

import { Handle, Position, type NodeProps } from "@xyflow/react";
import { Bot } from "lucide-react";
import { Badge } from "@/components/ui/badge";

function sessionBorderClass(data: Record<string, unknown>, selected: boolean): string {
  if (selected) return "border-emerald-500 ring-1 ring-emerald-500/30";
  if (data.resume_self) return "border-amber-500 ring-1 ring-amber-500/30";
  if (data.resume_from) return "border-blue-500 ring-1 ring-blue-500/30";
  return "border-border/50";
}

export function AgentNode({ data, selected }: NodeProps) {
  const name = (data.name as string) || String(data.id);
  const model = (data.model as string) || "default";
  const prompt = (data.prompt_template as string) || "";
  const preview = prompt.length > 60 ? prompt.slice(0, 60) + "…" : prompt;
  const resumeLabel = data.resume_self
    ? "resumes own session"
    : data.resume_from
      ? `resumes ${data.resume_from}`
      : null;

  return (
    <div
      className={`w-52 rounded-lg border-2 bg-card/90 px-3 py-2 shadow-sm ${sessionBorderClass(data, selected)}`}
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
      <div className="flex items-center gap-1 flex-wrap">
        <Badge variant="outline" className="text-[9px] px-1 py-0">
          {model}
        </Badge>
        {resumeLabel && (
          <Badge variant="outline" className={`text-[9px] px-1 py-0 ${data.resume_self ? "border-amber-500 text-amber-600" : "border-blue-500 text-blue-600"}`}>
            {resumeLabel}
          </Badge>
        )}
      </div>
      <Handle type="source" position={Position.Bottom} className="!bg-primary" />
    </div>
  );
}
