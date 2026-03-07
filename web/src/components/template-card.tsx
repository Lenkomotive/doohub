"use client";

import { Copy, Trash2 } from "lucide-react";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import type { PipelineTemplate } from "@/store/templates";

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

export function TemplateCard({
  template,
  onClick,
  onDuplicate,
  onDelete,
}: {
  template: PipelineTemplate;
  onClick?: () => void;
  onDuplicate: () => void;
  onDelete: () => void;
}) {
  const nodeCount = template.definition?.nodes?.length ?? 0;
  const agentCount = template.definition?.nodes?.filter(
    (n) => n.type === "claude_agent"
  ).length ?? 0;

  return (
    <Card
      className="border-border/50 bg-card/50 transition-colors hover:bg-accent/50 cursor-pointer"
      onClick={onClick}
    >
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <div className="flex-1 min-w-0 pr-2">
          <h3 className="text-sm font-medium truncate">{template.name}</h3>
          {template.description && (
            <p className="text-xs text-muted-foreground truncate mt-0.5">
              {template.description}
            </p>
          )}
        </div>
        <div className="flex items-center gap-1">
          <Badge variant="outline">{nodeCount} nodes</Badge>
          <Button
            variant="ghost"
            size="icon"
            className="h-7 w-7 text-muted-foreground hover:text-foreground"
            onClick={(e) => {
              e.stopPropagation();
              onDuplicate();
            }}
          >
            <Copy className="h-3.5 w-3.5" />
          </Button>
          <Button
            variant="ghost"
            size="icon"
            className="h-7 w-7 text-muted-foreground hover:text-destructive"
            onClick={(e) => {
              e.stopPropagation();
              onDelete();
            }}
          >
            <Trash2 className="h-3.5 w-3.5" />
          </Button>
        </div>
      </CardHeader>
      <CardContent className="flex items-center gap-3 text-xs text-muted-foreground">
        <span>
          {agentCount} agent{agentCount !== 1 ? "s" : ""}
        </span>
        <span>Updated {formatDate(template.updated_at)}</span>
      </CardContent>
    </Card>
  );
}
