"use client";

import { useEffect } from "react";
import { AlertTriangle, ExternalLink, GitMerge, Loader2, Trash2, XCircle } from "lucide-react";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import type { Pipeline } from "@/store/pipelines";
import { isActive, usePipelinesStore } from "@/store/pipelines";

const statusVariant: Record<string, "default" | "secondary" | "destructive" | "outline"> = {
  planning: "default",
  planned: "default",
  developing: "default",
  developed: "default",
  reviewing: "default",
  done: "outline",
  merged: "outline",
  failed: "destructive",
  cancelled: "secondary",
};

export function PipelineCard({
  pipeline,
  onCancel,
  onDelete,
}: {
  pipeline: Pipeline;
  onCancel: () => void;
  onDelete: () => void;
}) {
  const { mergeStatuses, mergingKeys, checkMergeStatus, mergePipeline } = usePipelinesStore();
  const title =
    pipeline.task_description ||
    pipeline.issue_title ||
    `Pipeline ${pipeline.pipeline_key}`;
  const repoName = pipeline.repo_path.split("/").pop() || pipeline.repo_path;

  const isDone = pipeline.status === "done" && !!pipeline.pr_number;
  const mergeStatus = mergeStatuses[pipeline.pipeline_key];
  const isMerging = mergingKeys.has(pipeline.pipeline_key);

  useEffect(() => {
    if (isDone && !mergeStatus) {
      checkMergeStatus(pipeline.pipeline_key);
    }
  }, [isDone, mergeStatus, pipeline.pipeline_key, checkMergeStatus]);

  return (
    <Card className="border-border/50 bg-card/50 transition-colors hover:bg-accent/50">
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
          {isDone && mergeStatus?.has_conflicts && pipeline.pr_url && (
            <a
              href={`${pipeline.pr_url}/conflicts`}
              target="_blank"
              rel="noopener noreferrer"
              onClick={(e) => e.stopPropagation()}
            >
              <Button variant="outline" size="sm" className="h-7 text-xs text-orange-600 border-orange-300 hover:bg-orange-50">
                <AlertTriangle className="h-3.5 w-3.5 mr-1" />
                Resolve Conflicts
              </Button>
            </a>
          )}
          {isDone && mergeStatus?.mergeable && !mergeStatus.has_conflicts && (
            <Button
              variant="outline"
              size="sm"
              className="h-7 text-xs text-green-600 border-green-300 hover:bg-green-50"
              disabled={isMerging}
              onClick={(e) => { e.stopPropagation(); mergePipeline(pipeline.pipeline_key); }}
            >
              {isMerging ? (
                <Loader2 className="h-3.5 w-3.5 mr-1 animate-spin" />
              ) : (
                <GitMerge className="h-3.5 w-3.5 mr-1" />
              )}
              Merge
            </Button>
          )}
          {isDone && !mergeStatus && (
            <Button variant="outline" size="sm" className="h-7 text-xs" disabled>
              <Loader2 className="h-3.5 w-3.5 mr-1 animate-spin" />
              Checking...
            </Button>
          )}
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
        {pipeline.error && (
          <span className="text-destructive truncate max-w-xs">{pipeline.error}</span>
        )}
      </CardContent>
    </Card>
  );
}
