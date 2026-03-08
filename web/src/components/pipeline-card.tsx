"use client";

import { useEffect, useState } from "react";
import { ExternalLink, GitMerge, Loader2, Trash2, XCircle, Workflow } from "lucide-react";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import type { Pipeline, MergeStatus } from "@/store/pipelines";
import { isActive } from "@/store/pipelines";
import { useLiveTimer } from "@/hooks/use-live-timer";
import { PipelineGraphSheet } from "@/components/pipeline-graph-sheet";

const statusVariant: Record<string, "default" | "secondary" | "destructive" | "outline"> = {
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
  const [graphOpen, setGraphOpen] = useState(false);
  const title =
    pipeline.issue_title ||
    pipeline.task_description ||
    `Pipeline ${pipeline.pipeline_key}`;
  const repoName = pipeline.repo_path.split("/").pop() || pipeline.repo_path;

  const pipelineIsActive = isActive(pipeline.status);
  const runningStep = pipelineIsActive
    ? pipeline.step_logs?.find((s) => s.status === "running")
    : null;
  const completedSteps = pipeline.step_logs?.filter((s) => s.status === "completed").length ?? 0;
  const totalSteps = pipeline.step_logs?.length ?? 0;

  const firstStep = pipeline.step_logs?.[0];
  const elapsed = useLiveTimer(firstStep?.started_at ?? null, pipelineIsActive);

  useEffect(() => {
    if (pipeline.status === "done" && pipeline.pr_number && !mergeStatus) {
      onCheckMergeStatus();
    }
  }, [pipeline.status, pipeline.pr_number, mergeStatus, onCheckMergeStatus]);

  const prConflictsUrl = pipeline.pr_url ? `${pipeline.pr_url}/conflicts` : null;

  return (
    <>
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
            {pipeline.template_id && (
              <Button
                variant="ghost"
                size="icon"
                className="h-7 w-7 text-muted-foreground hover:text-foreground"
                onClick={(e) => { e.stopPropagation(); setGraphOpen(true); }}
              >
                <Workflow className="h-3.5 w-3.5" />
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
            {pipelineIsActive && (
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
        <CardContent>
          <div className="flex items-center gap-3 text-xs text-muted-foreground">
            <span>{repoName}</span>
            <span>{pipeline.model}</span>
            {pipeline.total_cost_usd > 0 && (
              <span>${pipeline.total_cost_usd.toFixed(2)}</span>
            )}
            {elapsed && (
              <span className="text-blue-500">{elapsed}</span>
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
          </div>

          {/* Running step indicator */}
          {runningStep && (
            <div className="flex items-center gap-1 text-xs text-blue-500 mt-1.5">
              <Loader2 className="h-3 w-3 animate-spin" />
              <span className="truncate">{runningStep.node_name}</span>
            </div>
          )}

          {/* Progress bar for active pipelines */}
          {pipelineIsActive && totalSteps > 0 && (
            <div className="w-full h-1 bg-muted rounded-full mt-2 overflow-hidden">
              <div
                className="h-full bg-blue-500 rounded-full transition-all duration-500"
                style={{ width: `${(completedSteps / totalSteps) * 100}%` }}
              />
            </div>
          )}
        </CardContent>
      </Card>
      {pipeline.template_id && (
        <PipelineGraphSheet
          pipeline={pipeline}
          open={graphOpen}
          onClose={() => setGraphOpen(false)}
        />
      )}
    </>
  );
}
