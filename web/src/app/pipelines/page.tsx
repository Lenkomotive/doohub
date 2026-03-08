"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { GitBranch, Activity, CheckCircle2, XCircle as XCircleIcon, Ban } from "lucide-react";
import { apiFetch } from "@/lib/api";
import { AppShell } from "@/components/app-shell";
import { PipelineCard } from "@/components/pipeline-card";
import { CreatePipelineDialog } from "@/components/create-pipeline-dialog";
import { usePipelinesStore, isActive } from "@/store/pipelines";
import { SkeletonList } from "@/components/skeleton-card";

type StatusFilter = "all" | "running" | "completed" | "failed";

function PipelinesContent() {
  const router = useRouter();
  const [filter, setFilter] = useState<StatusFilter>("all");
  const {
    pipelines, total, isLoading, mergeStatuses,
    fetchPipelines, cancelPipeline, deletePipeline,
    checkMergeStatus, mergePipeline,
    connectSSE, disconnectSSE,
  } = usePipelinesStore();

  useEffect(() => {
    fetchPipelines();
    connectSSE();
    return () => disconnectSSE();
  }, [fetchPipelines, connectSSE, disconnectSSE]);

  const handleCheckMergeStatus = useCallback((key: string) => {
    checkMergeStatus(key);
  }, [checkMergeStatus]);

  const handleMerge = useCallback((key: string) => {
    mergePipeline(key);
  }, [mergePipeline]);

  const handleResolveConflicts = useCallback(async (pipeline: (typeof pipelines)[0]) => {
    const key = pipeline.pipeline_key;
    usePipelinesStore.setState((s) => ({
      mergeStatuses: { ...s.mergeStatuses, [key]: { ...s.mergeStatuses[key]!, resolvingConflicts: true } },
    }));
    try {
      const res = await apiFetch("/sessions", {
        method: "POST",
        body: JSON.stringify({ model: pipeline.model, project_path: pipeline.repo_path }),
      });
      const { session_key } = await res.json();
      router.push(`/sessions/${session_key}`);
    } catch {
      usePipelinesStore.setState((s) => ({
        mergeStatuses: { ...s.mergeStatuses, [key]: { ...s.mergeStatuses[key]!, resolvingConflicts: false } },
      }));
    }
  }, [router]);

  // Counts for summary bar
  const counts = useMemo(() => {
    let running = 0, completed = 0, failed = 0;
    for (const p of pipelines) {
      if (isActive(p.status)) running++;
      else if (p.status === "done" || p.status === "merged") completed++;
      else if (p.status === "failed" || p.status === "cancelled") failed++;
    }
    return { running, completed, failed };
  }, [pipelines]);

  // Filtered + sorted pipelines (running first, then by updated_at desc)
  const displayPipelines = useMemo(() => {
    let filtered = pipelines;
    switch (filter) {
      case "running":
        filtered = pipelines.filter((p) => isActive(p.status));
        break;
      case "completed":
        filtered = pipelines.filter((p) => p.status === "done" || p.status === "merged");
        break;
      case "failed":
        filtered = pipelines.filter((p) => p.status === "failed" || p.status === "cancelled");
        break;
    }
    return [...filtered].sort((a, b) => {
      const aActive = isActive(a.status) ? 1 : 0;
      const bActive = isActive(b.status) ? 1 : 0;
      if (aActive !== bActive) return bActive - aActive;
      return new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime();
    });
  }, [pipelines, filter]);

  const filterButtons: { key: StatusFilter; label: string; count: number; icon: React.ElementType; color: string }[] = [
    { key: "all", label: "All", count: total, icon: GitBranch, color: "text-foreground" },
    { key: "running", label: "Running", count: counts.running, icon: Activity, color: "text-blue-500" },
    { key: "completed", label: "Completed", count: counts.completed, icon: CheckCircle2, color: "text-green-500" },
    { key: "failed", label: "Failed", count: counts.failed, icon: XCircleIcon, color: "text-red-500" },
  ];

  return (
    <div className="p-6">
      {/* Header */}
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-lg font-medium">Pipelines</h2>
        <CreatePipelineDialog />
      </div>

      {/* Summary bar + filters */}
      {pipelines.length > 0 && (
        <div className="mb-4 flex items-center gap-1 rounded-lg bg-muted/50 p-1">
          {filterButtons.map(({ key, label, count, icon: Icon, color }) => (
            <button
              key={key}
              onClick={() => setFilter(key)}
              className={`flex items-center gap-1.5 rounded-md px-3 py-1.5 text-xs font-medium transition-colors ${
                filter === key
                  ? "bg-background text-foreground shadow-sm"
                  : "text-muted-foreground hover:text-foreground"
              }`}
            >
              <Icon className={`h-3 w-3 ${filter === key ? color : ""}`} />
              {label}
              <span className={`tabular-nums ${filter === key ? color : "text-muted-foreground"}`}>
                {count}
              </span>
            </button>
          ))}
        </div>
      )}

      {isLoading && pipelines.length === 0 ? (
        <SkeletonList count={4} />
      ) : pipelines.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-20 text-center">
          <GitBranch className="mb-3 h-8 w-8 text-muted-foreground/50" />
          <p className="text-sm text-muted-foreground">No pipelines</p>
        </div>
      ) : displayPipelines.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-12 text-center">
          <Ban className="mb-3 h-6 w-6 text-muted-foreground/50" />
          <p className="text-sm text-muted-foreground">No {filter} pipelines</p>
        </div>
      ) : (
        <div className="grid gap-2">
          {displayPipelines.map((pipeline) => (
            <PipelineCard
              key={pipeline.pipeline_key}
              pipeline={pipeline}
              mergeStatus={mergeStatuses[pipeline.pipeline_key]}
              onClick={() => router.push(`/pipelines/${pipeline.pipeline_key}`)}
              onCancel={() => cancelPipeline(pipeline.pipeline_key)}
              onDelete={() => deletePipeline(pipeline.pipeline_key)}
              onCheckMergeStatus={() => handleCheckMergeStatus(pipeline.pipeline_key)}
              onMerge={() => handleMerge(pipeline.pipeline_key)}
              onResolveConflicts={() => handleResolveConflicts(pipeline)}
            />
          ))}
        </div>
      )}
    </div>
  );
}

export default function PipelinesPage() {
  return (
    <AppShell>
      <PipelinesContent />
    </AppShell>
  );
}
