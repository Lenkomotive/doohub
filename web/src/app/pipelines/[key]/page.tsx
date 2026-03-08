"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Markdown from "react-markdown";
import {
  ArrowLeft,
  ExternalLink,
  GitMerge,
  Loader2,
  Trash2,
  XCircle,
  ChevronDown,
  ChevronRight,
  CheckCircle2,
  Circle,
  AlertCircle,
  Bot,
  GitFork,
  Play,
  Flag,
  SkipForward,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { AppShell } from "@/components/app-shell";
import { usePipelinesStore, isActive } from "@/store/pipelines";
import type { Pipeline, StepLog } from "@/store/pipelines";

const stepNodeIcon: Record<string, React.ElementType> = {
  start: Play,
  end: Flag,
  failed: AlertCircle,
  claude_agent: Bot,
  condition: GitFork,
};

const stepStatusIcon = (status: string) => {
  switch (status) {
    case "completed":
      return <CheckCircle2 className="h-4 w-4 text-green-500" />;
    case "running":
      return <Loader2 className="h-4 w-4 animate-spin text-blue-500" />;
    case "failed":
      return <AlertCircle className="h-4 w-4 text-destructive" />;
    case "skipped":
      return <SkipForward className="h-4 w-4 text-muted-foreground" />;
    default:
      return <Circle className="h-3.5 w-3.5 text-muted-foreground" />;
  }
};

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

function StepOutput({ text }: { text: string }) {
  const [expanded, setExpanded] = useState(false);
  const isLong = text.length > 120;
  if (!isLong) {
    return <p className="text-xs text-muted-foreground mt-1 truncate">{text}</p>;
  }
  return (
    <div className="mt-1">
      <button
        className="text-xs text-muted-foreground hover:text-foreground/70 truncate block w-full text-left"
        onClick={() => setExpanded(!expanded)}
      >
        {expanded ? "▾ collapse" : text}
      </button>
      {expanded && (
        <div className="mt-2 text-xs prose prose-sm prose-invert max-w-none rounded-md bg-muted/50 p-3 max-h-96 overflow-y-auto">
          <Markdown>{text}</Markdown>
        </div>
      )}
    </div>
  );
}

function PipelineDetail() {
  const params = useParams();
  const router = useRouter();
  const pipelineKey = params.key as string;
  const [planExpanded, setPlanExpanded] = useState(false);

  const {
    pipelines,
    mergeStatuses,
    fetchPipelines,
    cancelPipeline,
    deletePipeline,
    checkMergeStatus,
    mergePipeline,
    resolveConflicts,
    connectSSE,
    disconnectSSE,
  } = usePipelinesStore();

  useEffect(() => {
    fetchPipelines();
    connectSSE();
    return () => disconnectSSE();
  }, [fetchPipelines, connectSSE, disconnectSSE]);

  const pipeline = pipelines.find((p) => p.pipeline_key === pipelineKey);
  const mergeStatus = mergeStatuses[pipelineKey];

  const handleCheckMergeStatus = useCallback(() => {
    checkMergeStatus(pipelineKey);
  }, [checkMergeStatus, pipelineKey]);

  useEffect(() => {
    if (pipeline?.status === "done" && pipeline.pr_number && !mergeStatus) {
      handleCheckMergeStatus();
    }
  }, [pipeline?.status, pipeline?.pr_number, mergeStatus, handleCheckMergeStatus]);

  const handleCancel = async () => {
    await cancelPipeline(pipelineKey);
  };

  const handleDelete = async () => {
    await deletePipeline(pipelineKey);
    router.push("/pipelines");
  };

  const handleMerge = async () => {
    await mergePipeline(pipelineKey);
  };

  const handleResolveConflicts = async () => {
    await resolveConflicts(pipelineKey);
  };

  if (pipelines.length === 0) {
    return (
      <div className="flex h-full items-center justify-center">
        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (!pipeline) {
    return (
      <div className="p-6">
        <Button variant="ghost" size="sm" onClick={() => router.push("/pipelines")}>
          <ArrowLeft className="mr-2 h-4 w-4" />
          Back to pipelines
        </Button>
        <div className="flex flex-col items-center justify-center py-20 text-center">
          <p className="text-sm text-muted-foreground">Pipeline not found</p>
        </div>
      </div>
    );
  }

  const title =
    pipeline.issue_title ||
    pipeline.task_description ||
    `Pipeline ${pipeline.pipeline_key}`;
  const repoName = pipeline.repo_path.split("/").pop() || pipeline.repo_path;
  return (
    <div className="p-6 max-w-3xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3 min-w-0">
          <Button
            variant="ghost"
            size="icon"
            className="h-8 w-8 shrink-0"
            onClick={() => router.push("/pipelines")}
          >
            <ArrowLeft className="h-4 w-4" />
          </Button>
          <div className="min-w-0">
            <div className="flex items-center gap-2">
              <h1 className="text-lg font-medium truncate">{title}</h1>
              <Badge variant={statusVariant[pipeline.status] || "secondary"}>
                {pipeline.status}
              </Badge>
            </div>
            {pipeline.issue_number && (
              <span className="text-sm text-muted-foreground">#{pipeline.issue_number}</span>
            )}
          </div>
        </div>
        <div className="flex items-center gap-1 shrink-0">
          {pipeline.pr_url && (
            <a href={pipeline.pr_url} target="_blank" rel="noopener noreferrer">
              <Button variant="ghost" size="icon" className="h-8 w-8">
                <ExternalLink className="h-4 w-4" />
              </Button>
            </a>
          )}
          {isActive(pipeline.status) && (
            <Button variant="ghost" size="icon" className="h-8 w-8" onClick={handleCancel}>
              <XCircle className="h-4 w-4" />
            </Button>
          )}
          <Button
            variant="ghost"
            size="icon"
            className="h-8 w-8 text-destructive"
            onClick={handleDelete}
          >
            <Trash2 className="h-4 w-4" />
          </Button>
        </div>
      </div>

      {/* Info */}
      <Card className="mb-4 border-border/50 bg-card/50">
        <CardContent className="pt-4">
          <div className="grid grid-cols-2 gap-3 text-sm">
            <div>
              <span className="text-muted-foreground">Repository</span>
              <p className="font-medium">{repoName}</p>
            </div>
            <div>
              <span className="text-muted-foreground">Created</span>
              <p className="font-medium">{new Date(pipeline.created_at).toLocaleString()}</p>
            </div>
            {pipeline.pr_number && (
              <div>
                <span className="text-muted-foreground">PR</span>
                <p className="font-medium">
                  {pipeline.pr_url ? (
                    <a
                      href={pipeline.pr_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-primary hover:underline"
                    >
                      #{pipeline.pr_number}
                    </a>
                  ) : (
                    `#${pipeline.pr_number}`
                  )}
                </p>
              </div>
            )}
            {pipeline.template_name && (
              <div>
                <span className="text-muted-foreground">Template</span>
                <p className="font-medium">{pipeline.template_name}</p>
              </div>
            )}
            {pipeline.total_cost_usd > 0 && (
              <div>
                <span className="text-muted-foreground">Cost</span>
                <p className="font-medium">${pipeline.total_cost_usd.toFixed(2)}</p>
              </div>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Error */}
      {pipeline.error && (
        <Card className="mb-4 border-destructive/50 bg-destructive/5">
          <CardContent className="pt-4">
            <p className="text-sm text-destructive">{pipeline.error}</p>
          </CardContent>
        </Card>
      )}

      {/* Merge controls */}
      {pipeline.status === "done" && mergeStatus && (
        <Card className="mb-4 border-border/50 bg-card/50">
          <CardContent className="pt-4 flex items-center gap-3">
            {mergeStatus.checking && (
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <Loader2 className="h-4 w-4 animate-spin" />
                Checking merge status...
              </div>
            )}
            {!mergeStatus.checking && mergeStatus.already_merged && (
              <span className="text-sm text-muted-foreground">Already merged</span>
            )}
            {!mergeStatus.checking && mergeStatus.has_conflicts && (
              <Button
                variant="outline"
                size="sm"
                className="border-orange-500 text-orange-500 hover:bg-orange-500/10"
                disabled={mergeStatus.resolvingConflicts}
                onClick={handleResolveConflicts}
              >
                {mergeStatus.resolvingConflicts ? (
                  <Loader2 className="h-4 w-4 animate-spin mr-2" />
                ) : null}
                {mergeStatus.resolvingConflicts ? "Starting session..." : "Resolve Conflicts"}
              </Button>
            )}
            {!mergeStatus.checking && mergeStatus.mergeable && !mergeStatus.has_conflicts && (
              <Button
                variant="outline"
                size="sm"
                className="border-green-500 text-green-500 hover:bg-green-500/10"
                disabled={mergeStatus.merging}
                onClick={handleMerge}
              >
                {mergeStatus.merging ? (
                  <Loader2 className="h-4 w-4 animate-spin mr-2" />
                ) : (
                  <GitMerge className="h-4 w-4 mr-2" />
                )}
                Merge PR
              </Button>
            )}
            {!mergeStatus.checking && mergeStatus.error && (
              <span className="text-sm text-destructive">{mergeStatus.error}</span>
            )}
          </CardContent>
        </Card>
      )}

      {/* Steps */}
      {pipeline.step_logs && pipeline.step_logs.length > 0 && (
        <Card className="mb-4 border-border/50 bg-card/50">
          <CardHeader className="pb-2">
            <h3 className="text-sm font-medium">Steps</h3>
          </CardHeader>
          <CardContent>
            <div className="space-y-0">
              {pipeline.step_logs.map((step, i) => {
                const NodeIcon = stepNodeIcon[step.node_type] || Circle;
                return (
                  <div key={`${step.node_id}-${i}`} className="flex items-start gap-3 py-2 border-b border-border/30 last:border-0">
                    <div className="mt-0.5 shrink-0">{stepStatusIcon(step.status)}</div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <NodeIcon className="h-3.5 w-3.5 text-muted-foreground shrink-0" />
                        <span className="text-sm font-medium truncate">{step.node_name}</span>
                        <span className="text-xs text-muted-foreground">{step.node_type}</span>
                        {step.duration_s != null && (
                          <span className="text-xs text-muted-foreground ml-auto shrink-0">
                            {step.duration_s < 60
                              ? `${step.duration_s}s`
                              : `${Math.floor(step.duration_s / 60)}m ${Math.round(step.duration_s % 60)}s`}
                          </span>
                        )}
                      </div>
                      {step.output && (
                        <StepOutput text={step.output} />
                      )}
                      {step.error && (
                        <p className="text-xs text-destructive mt-1">{step.error}</p>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Plan */}
      {pipeline.plan && (
        <Card className="mb-4 border-border/50 bg-card/50">
          <CardHeader
            className="flex flex-row items-center gap-2 cursor-pointer select-none pb-2"
            onClick={() => setPlanExpanded(!planExpanded)}
          >
            {planExpanded ? (
              <ChevronDown className="h-4 w-4 text-muted-foreground" />
            ) : (
              <ChevronRight className="h-4 w-4 text-muted-foreground" />
            )}
            <h3 className="text-sm font-medium">Plan</h3>
          </CardHeader>
          {planExpanded && (
            <CardContent>
              <div className="text-sm prose prose-sm dark:prose-invert max-w-none bg-muted/50 rounded-md p-3 max-h-96 overflow-y-auto">
                <Markdown>{pipeline.plan}</Markdown>
              </div>
            </CardContent>
          )}
        </Card>
      )}
    </div>
  );
}

export default function PipelineDetailPage() {
  return (
    <AppShell>
      <PipelineDetail />
    </AppShell>
  );
}
