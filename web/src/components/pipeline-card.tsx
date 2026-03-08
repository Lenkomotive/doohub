"use client";

import { useEffect, useState } from "react";
import {
  ExternalLink,
  GitMerge,
  Loader2,
  Trash2,
  XCircle,
  Clock,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import type { Pipeline, MergeStatus, StepLog } from "@/store/pipelines";
import { isActive } from "@/store/pipelines";

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

const statusColor: Record<string, string> = {
  planning: "bg-blue-500",
  planned: "bg-blue-500",
  developing: "bg-blue-500",
  developed: "bg-blue-500",
  reviewing: "bg-blue-500",
  running: "bg-blue-500",
  starting: "bg-blue-500",
  done: "bg-green-500",
  merged: "bg-purple-500",
  failed: "bg-red-500",
  cancelled: "bg-zinc-500",
};

const accentColors: Record<string, string> = {
  planning: "border-l-blue-500",
  planned: "border-l-blue-500",
  developing: "border-l-blue-500",
  developed: "border-l-blue-500",
  reviewing: "border-l-blue-500",
  running: "border-l-blue-500",
  starting: "border-l-blue-500",
  done: "border-l-green-500",
  merged: "border-l-purple-500",
  failed: "border-l-red-500",
  cancelled: "border-l-zinc-500",
};

function formatDuration(seconds: number): string {
  if (seconds < 60) return `${Math.round(seconds)}s`;
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ${Math.round(seconds % 60)}s`;
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  return `${h}h ${m}m`;
}

function ElapsedTimer({ since }: { since: string }) {
  const [elapsed, setElapsed] = useState(0);

  useEffect(() => {
    const start = new Date(since).getTime();
    const tick = () => setElapsed(Math.floor((Date.now() - start) / 1000));
    tick();
    const id = setInterval(tick, 1000);
    return () => clearInterval(id);
  }, [since]);

  return <span>{formatDuration(elapsed)}</span>;
}

function NodeProgressDots({ steps }: { steps: StepLog[] }) {
  const displaySteps = steps.filter(
    (s) => s.node_type !== "start" && s.node_type !== "end" && s.node_type !== "failed"
  );
  if (displaySteps.length === 0) return null;

  return (
    <div className="flex items-center gap-0.5">
      {displaySteps.map((step, i) => {
        let cls = "h-1.5 w-1.5 rounded-full ";
        switch (step.status) {
          case "completed": cls += "bg-green-500"; break;
          case "running": cls += "bg-blue-500 animate-pulse"; break;
          case "failed": cls += "bg-red-500"; break;
          case "skipped": cls += "bg-zinc-600"; break;
          default: cls += "bg-zinc-700";
        }
        return <div key={`${step.node_id}-${i}`} className={cls} title={`${step.node_name} (${step.status})`} />;
      })}
    </div>
  );
}

export function PipelineCard({
  pipeline,
  mergeStatus,
  onClick,
  onCancel,
  onDelete,
  onCheckMergeStatus,
  onMerge,
  onResolveConflicts,
}: {
  pipeline: Pipeline;
  mergeStatus?: MergeStatus;
  onClick?: () => void;
  onCancel: () => void;
  onDelete: () => void;
  onCheckMergeStatus: () => void;
  onMerge: () => void;
  onResolveConflicts: () => void;
}) {
  const title =
    pipeline.issue_title ||
    pipeline.task_description ||
    `Pipeline ${pipeline.pipeline_key}`;
  const repoName = pipeline.repo_path.split("/").pop() || pipeline.repo_path;
  const active = isActive(pipeline.status);
  const steps = pipeline.step_logs || [];
  const runningStep = steps.find((s) => s.status === "running");
  const completedWork = steps.filter((s) => s.status === "completed" && s.node_type !== "start" && s.node_type !== "end");
  const totalSteps = pipeline.total_steps || 0;
  const totalDuration = steps.reduce((sum, s) => sum + (s.duration_s || 0), 0);

  useEffect(() => {
    if (pipeline.status === "done" && pipeline.pr_number && !mergeStatus) {
      onCheckMergeStatus();
    }
  }, [pipeline.status, pipeline.pr_number, mergeStatus, onCheckMergeStatus]);

  return (
    <div
      className={`group border-l-2 ${accentColors[pipeline.status] || "border-l-transparent"} rounded-md border border-border/40 bg-card/50 px-3 py-2 transition-colors hover:bg-accent/50 cursor-pointer`}
      onClick={onClick}
    >
      {/* Line 1: Title + badge + actions */}
      <div className="flex items-center gap-2 min-w-0">
        {active && (
          <span className="relative flex h-1.5 w-1.5 shrink-0">
            <span className={`absolute inline-flex h-full w-full rounded-full opacity-75 animate-ping ${statusColor[pipeline.status] || "bg-blue-500"}`} />
            <span className={`relative inline-flex rounded-full h-1.5 w-1.5 ${statusColor[pipeline.status] || "bg-blue-500"}`} />
          </span>
        )}
        <span className="text-sm font-medium truncate">{title}</span>
        {pipeline.issue_number && (
          <span className="text-[11px] text-muted-foreground shrink-0">#{pipeline.issue_number}</span>
        )}
        <div className="flex-1" />
        <Badge variant={statusVariant[pipeline.status] || "secondary"} className="text-[10px] h-5 shrink-0">
          {pipeline.status}
        </Badge>
        <div className="flex items-center shrink-0 opacity-0 group-hover:opacity-100 transition-opacity">
          {pipeline.pr_url && (
            <a href={pipeline.pr_url} target="_blank" rel="noopener noreferrer" onClick={(e) => e.stopPropagation()}>
              <Button variant="ghost" size="icon" className="h-6 w-6 text-muted-foreground"><ExternalLink className="h-3 w-3" /></Button>
            </a>
          )}
          {active && (
            <Button variant="ghost" size="icon" className="h-6 w-6 text-muted-foreground hover:text-foreground" onClick={(e) => { e.stopPropagation(); onCancel(); }}>
              <XCircle className="h-3 w-3" />
            </Button>
          )}
          <Button variant="ghost" size="icon" className="h-6 w-6 text-muted-foreground hover:text-destructive" onClick={(e) => { e.stopPropagation(); onDelete(); }}>
            <Trash2 className="h-3 w-3" />
          </Button>
        </div>
      </div>

      {/* Line 2: Meta row */}
      <div className="flex items-center gap-2 mt-1 text-[11px] text-muted-foreground">
        <span>{repoName}</span>
        {pipeline.template_name && (
          <>
            <span className="text-border">·</span>
            <span>{pipeline.template_name}</span>
          </>
        )}
        {steps.length > 0 && (
          <>
            <span className="text-border">·</span>
            <NodeProgressDots steps={steps} />
            {totalSteps > 0 && (
              <span>{completedWork.length}/{totalSteps}</span>
            )}
          </>
        )}
        <div className="flex-1" />
        {pipeline.total_cost_usd > 0 && (
          <span>${pipeline.total_cost_usd.toFixed(2)}</span>
        )}
        <span className="flex items-center gap-0.5">
          <Clock className="h-2.5 w-2.5" />
          {active ? <ElapsedTimer since={pipeline.created_at} /> : formatDuration(totalDuration)}
        </span>
      </div>

      {/* Line 3 (conditional): Running step activity */}
      {active && runningStep && (
        <div className="flex items-center gap-1.5 mt-1 text-[11px]">
          <Loader2 className="h-2.5 w-2.5 animate-spin text-blue-500 shrink-0" />
          <span className="text-blue-400 truncate">{runningStep.node_name}</span>
          {runningStep.started_at && (
            <span className="text-muted-foreground shrink-0"><ElapsedTimer since={runningStep.started_at} /></span>
          )}
        </div>
      )}

      {/* Error */}
      {pipeline.error && (
        <div className="mt-1 text-[11px] text-destructive truncate">{pipeline.error}</div>
      )}

      {/* Merge controls */}
      {pipeline.status === "done" && mergeStatus && (
        <div className="flex items-center gap-2 mt-1 text-[11px]">
          {mergeStatus.checking && <Loader2 className="h-3 w-3 animate-spin" />}
          {!mergeStatus.checking && mergeStatus.already_merged && (
            <span className="text-muted-foreground">Already merged</span>
          )}
          {!mergeStatus.checking && mergeStatus.has_conflicts && (
            <Button
              variant="outline"
              size="sm"
              className="h-5 text-[10px] px-2 border-orange-500 text-orange-500 hover:bg-orange-500/10"
              disabled={mergeStatus.resolvingConflicts}
              onClick={(e) => { e.stopPropagation(); onResolveConflicts(); }}
            >
              {mergeStatus.resolvingConflicts ? <Loader2 className="h-2.5 w-2.5 animate-spin mr-1" /> : null}
              {mergeStatus.resolvingConflicts ? "Starting..." : "Resolve Conflicts"}
            </Button>
          )}
          {!mergeStatus.checking && mergeStatus.mergeable && !mergeStatus.has_conflicts && (
            <Button
              variant="outline"
              size="sm"
              className="h-5 text-[10px] px-2 border-green-500 text-green-500 hover:bg-green-500/10"
              disabled={mergeStatus.merging}
              onClick={(e) => { e.stopPropagation(); onMerge(); }}
            >
              {mergeStatus.merging ? <Loader2 className="h-2.5 w-2.5 animate-spin mr-1" /> : <GitMerge className="h-2.5 w-2.5 mr-1" />}
              Merge
            </Button>
          )}
          {!mergeStatus.checking && mergeStatus.error && (
            <span className="text-destructive truncate max-w-[200px]">{mergeStatus.error}</span>
          )}
        </div>
      )}
    </div>
  );
}
