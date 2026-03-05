"use client";

import { useCallback, useEffect } from "react";
import { useRouter } from "next/navigation";
import { GitBranch } from "lucide-react";
import { AppShell } from "@/components/app-shell";
import { PipelineCard } from "@/components/pipeline-card";
import { CreatePipelineDialog } from "@/components/create-pipeline-dialog";
import { usePipelinesStore } from "@/store/pipelines";
import { SkeletonList } from "@/components/skeleton-card";

function PipelinesContent() {
  const router = useRouter();
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

  return (
    <div className="p-6">
      <div className="mb-4 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <h2 className="text-lg font-medium">Pipelines</h2>
          <span className="text-sm text-muted-foreground">({total})</span>
        </div>
        <CreatePipelineDialog />
      </div>

      {isLoading && pipelines.length === 0 ? (
        <SkeletonList count={4} />
      ) : pipelines.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-20 text-center">
          <GitBranch className="mb-3 h-8 w-8 text-muted-foreground/50" />
          <p className="text-sm text-muted-foreground">No pipelines</p>
        </div>
      ) : (
        <div className="grid gap-3">
          {pipelines.map((pipeline) => (
            <PipelineCard
              key={pipeline.pipeline_key}
              pipeline={pipeline}
              mergeStatus={mergeStatuses[pipeline.pipeline_key]}
              onClick={() => router.push(`/pipelines/${pipeline.pipeline_key}`)}
              onCancel={() => cancelPipeline(pipeline.pipeline_key)}
              onDelete={() => deletePipeline(pipeline.pipeline_key)}
              onCheckMergeStatus={() => handleCheckMergeStatus(pipeline.pipeline_key)}
              onMerge={() => handleMerge(pipeline.pipeline_key)}
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
