"use client";

import { Clock, GitBranch, GitPullRequest, AlertCircle } from "lucide-react";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import type { Pipeline } from "@/store/sessions";

const statusVariant: Record<string, "default" | "secondary" | "destructive" | "outline"> = {
  planning: "default",
  planned: "secondary",
  developing: "default",
  developed: "secondary",
  reviewing: "default",
  done: "outline",
  failed: "destructive",
};

function timeAgo(dateStr: string): string {
  const seconds = Math.floor(
    (Date.now() - new Date(dateStr).getTime()) / 1000
  );
  if (seconds < 60) return "just now";
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}

export function PipelineCard({
  pipeline,
  onClick,
}: {
  pipeline: Pipeline;
  onClick: () => void;
}) {
  return (
    <Card
      className="tap-target cursor-pointer border-border/50 bg-card/50 transition-colors hover:bg-accent/50 active:scale-[0.97] active:opacity-80"
      onClick={onClick}
    >
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <h3 className="text-sm font-medium">
          #{pipeline.issue_number} {pipeline.issue_title}
        </h3>
        <Badge variant={statusVariant[pipeline.status] || "secondary"}>
          {pipeline.status}
        </Badge>
      </CardHeader>
      <CardContent className="space-y-1">
        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          <GitBranch className="h-3 w-3" />
          {pipeline.repo}
        </div>
        {pipeline.branch && (
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <GitBranch className="h-3 w-3" />
            {pipeline.branch}
          </div>
        )}
        {pipeline.pr_number && (
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <GitPullRequest className="h-3 w-3" />
            PR #{pipeline.pr_number}
            {pipeline.review_round > 0 && ` (review round ${pipeline.review_round})`}
          </div>
        )}
        {pipeline.error && (
          <div className="flex items-center gap-2 text-xs text-destructive">
            <AlertCircle className="h-3 w-3" />
            {pipeline.error.slice(0, 80)}
          </div>
        )}
        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          <Clock className="h-3 w-3" />
          {timeAgo(pipeline.updated_at)}
        </div>
      </CardContent>
    </Card>
  );
}
