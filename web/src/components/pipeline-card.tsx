"use client";

import { useEffect } from "react";
import { ExternalLink, GitMerge, Loader2, Trash2, XCircle } from "lucide-react";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import type { Pipeline, MergeStatus } from "@/store/pipelines";
import { isActive } from "@/store/pipelines";

function formatTokens(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}k`;
  return String(n);
}

const statusVariant: Record<string, "default" | "secondary" | "destructive" | "outline"> = {
  checking_dependencies: "default",
  blocked: "destructive",
  planning: "default",
  planned: "default",
  developing: "default",
  developed: "default",
  reviewing: "default",
  done: "outline",
  merged: "secondary",
  failed: "destructive",
  cancelled: "secondary",
};

export function PipelineCard({
  pipeline,
  mergeStatus,
  onClick,
  onCancel,
  onDelete,
  onCheckMergeStatus,
  onMerge,
}: {
  pipeline: Pipeline;
  mergeStatus?: MergeStatus;
  onClick?: () => void;
  onCancel: () => void;
  onDelete: () => void;
  onCheckMergeStatus: () => void;
  onMerge: () => void;
}) {
  const title =
    pipeline.issue_title ||
    pipeline.task_description ||
    `Pipeline ${pipeline.pipeline_key}`;
  const repoName = pipeline.repo_path.split("/").pop() || pipeline.repo_path;

  useEffect(() => {
    if (pipeline.status === "done" && pipeline.pr_number && !mergeStatus) {
      onCheckMergeStatus();
    }
  }, [pipeline.status, pipeline.pr_number, mergeStatus, onCheckMergeStatus]);

  const prConflictsUrl = pipeline.pr_url ? `${pipeline.pr_url}/conflicts` : null;

  return (
    <Card className="border-border/50 bg-card/50 transition-colors hover:bg-accent/50 cursor-pointer" onClick={onClick}>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <div className="flex-1 min-w-0 pr-2">
          <h3 className="text-sm font-medium truncate">{title}</h3>
          {pipeline.issue_number && (
            <span className="text-xs text-muted-foreground">#{pipeline.issue_number}</span>
          )}
        </div>
        <div className="flex items-center gap-1">
          <Badge variant={statusVariant[pipeline.status] || "secondary"}>
            {pipeline.status}
          </Badge>
          {pipeline.pr_url && (
            <a
              href={pipeline.pr_url}
              target="_blank"
              rel="noopener noreferrer"
              onClick={(e) => e.stopPropagation()}
            >
              <Button variant="ghost" size="icon" className="h-7 w-7 text-muted-foreground">
                <ExternalLink className="h-3.5 w-3.5" />
              </Button>
            </a>
          )}
          {isActive(pipeline.status) && (
            <Button
              variant="ghost"
              size="icon"
              className="h-7 w-7 text-muted-foreground hover:text-foreground"
              onClick={(e) => { e.stopPropagation(); onCancel(); }}
            >
              <XCircle className="h-3.5 w-3.5" />
            </Button>
          )}
          <Button
            variant="ghost"
            size="icon"
            className="h-7 w-7 text-muted-foreground hover:text-destructive"
            onClick={(e) => { e.stopPropagation(); onDelete(); }}
          >
            <Trash2 className="h-3.5 w-3.5" />
          </Button>
        </div>
      </CardHeader>
      <CardContent className="flex items-center gap-3 text-xs text-muted-foreground">
        <span>{repoName}</span>
        <span>{pipeline.model}</span>
        {pipeline.total_cost_usd > 0 && (
          <span>${pipeline.total_cost_usd.toFixed(2)}</span>
        )}
        {(pipeline.input_tokens > 0 || pipeline.output_tokens > 0) && (
          <span>{formatTokens(pipeline.input_tokens + pipeline.output_tokens)} tokens</span>
        )}
        {pipeline.error && (
          <span className="text-destructive truncate max-w-xs">{pipeline.error}</span>
        )}

        {/* Merge controls for done pipelines */}
        {pipeline.status === "done" && mergeStatus && (
          <div className="ml-auto flex items-center gap-2">
            {mergeStatus.checking && (
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
            )}
            {!mergeStatus.checking && mergeStatus.already_merged && (
              <span className="text-muted-foreground">Already merged</span>
            )}
            {!mergeStatus.checking && mergeStatus.has_conflicts && prConflictsUrl && (
              <a href={prConflictsUrl} target="_blank" rel="noopener noreferrer" onClick={(e) => e.stopPropagation()}>
                <Button variant="outline" size="sm" className="h-6 text-xs border-orange-500 text-orange-500 hover:bg-orange-500/10">
                  Resolve Conflicts
                </Button>
              </a>
            )}
            {!mergeStatus.checking && mergeStatus.mergeable && !mergeStatus.has_conflicts && (
              <Button
                variant="outline"
                size="sm"
                className="h-6 text-xs border-green-500 text-green-500 hover:bg-green-500/10"
                disabled={mergeStatus.merging}
                onClick={(e) => { e.stopPropagation(); onMerge(); }}
              >
                {mergeStatus.merging ? <Loader2 className="h-3 w-3 animate-spin mr-1" /> : <GitMerge className="h-3 w-3 mr-1" />}
                Merge
              </Button>
            )}
            {!mergeStatus.checking && mergeStatus.error && (
              <span className="text-destructive text-xs truncate max-w-[200px]">{mergeStatus.error}</span>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
