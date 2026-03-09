"use client";

import { Trash2, Bot, Copy } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import type { PipelineTemplate } from "@/store/templates";

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
  });
}

export function TemplateCard({
  template,
  onClick,
  onDelete,
  onDuplicate,
}: {
  template: PipelineTemplate;
  onClick?: () => void;
  onDelete: () => void;
  onDuplicate: () => void;
}) {
  const nodeCount = template.definition?.nodes?.length ?? 0;
  const agentCount = template.definition?.nodes?.filter(
    (n) => n.type === "claude_agent"
  ).length ?? 0;

  return (
    <div
      className="group flex items-center gap-2 rounded-md border border-border/40 bg-card/50 px-3 py-2 transition-colors hover:bg-accent/50 cursor-pointer"
      onClick={onClick}
    >
      <span className="text-sm font-medium truncate">{template.name}</span>
      {template.description && (
        <>
          <span className="text-border">·</span>
          <span className="text-[11px] text-muted-foreground truncate hidden sm:inline">{template.description}</span>
        </>
      )}
      <div className="flex-1" />
      <span className="flex items-center gap-0.5 text-[11px] text-muted-foreground shrink-0">
        <Bot className="h-2.5 w-2.5" />
        {agentCount}
      </span>
      <Badge variant="outline" className="text-[10px] h-5 shrink-0">{nodeCount} nodes</Badge>
      <span className="text-[11px] text-muted-foreground shrink-0">{formatDate(template.updated_at)}</span>
      <Button
        variant="ghost"
        size="icon"
        className="h-6 w-6 text-muted-foreground opacity-0 group-hover:opacity-100 shrink-0"
        onClick={(e) => { e.stopPropagation(); onDuplicate(); }}
      >
        <Copy className="h-3 w-3" />
      </Button>
      <Button
        variant="ghost"
        size="icon"
        className="h-6 w-6 text-muted-foreground opacity-0 group-hover:opacity-100 hover:text-destructive shrink-0"
        onClick={(e) => { e.stopPropagation(); onDelete(); }}
      >
        <Trash2 className="h-3 w-3" />
      </Button>
    </div>
  );
}
