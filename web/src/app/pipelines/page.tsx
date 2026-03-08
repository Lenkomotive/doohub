"use client";

import { useCallback, useEffect } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { GitBranch, Search } from "lucide-react";
import { AppShell } from "@/components/app-shell";
import { PipelineCard } from "@/components/pipeline-card";
import { CreatePipelineDialog } from "@/components/create-pipeline-dialog";
import { usePipelinesStore, useFilteredPipelines } from "@/store/pipelines";
import { SkeletonList } from "@/components/skeleton-card";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

function PipelinesContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const {
    total, isLoading, mergeStatuses,
    filters, setFilters,
    fetchPipelines, cancelPipeline, deletePipeline,
    checkMergeStatus, mergePipeline,
    connectSSE, disconnectSSE,
  } = usePipelinesStore();

  const filteredPipelines = useFilteredPipelines();

  // Apply URL param filter on mount
  useEffect(() => {
    const statusParam = searchParams.get("status");
    if (statusParam) {
      setFilters({ status: statusParam });
    }
  }, [searchParams, setFilters]);

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

      {/* Filter controls */}
      <div className="mb-4 flex items-center gap-3">
        <Select
          value={filters.status ?? "all"}
          onValueChange={(v) => setFilters({ status: v === "all" ? null : v })}
        >
          <SelectTrigger size="sm" className="w-36">
            <SelectValue placeholder="All statuses" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All statuses</SelectItem>
            <SelectItem value="running">Running</SelectItem>
            <SelectItem value="completed">Completed</SelectItem>
            <SelectItem value="failed">Failed</SelectItem>
            <SelectItem value="cancelled">Cancelled</SelectItem>
          </SelectContent>
        </Select>
        <div className="relative flex-1 max-w-xs">
          <Search className="absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted-foreground" />
          <Input
            placeholder="Search pipelines..."
            value={filters.search}
            onChange={(e) => setFilters({ search: e.target.value })}
            className="h-8 pl-8 text-sm"
          />
        </div>
      </div>

      {isLoading && filteredPipelines.length === 0 ? (
        <SkeletonList count={4} />
      ) : filteredPipelines.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-20 text-center">
          <GitBranch className="mb-3 h-8 w-8 text-muted-foreground/50" />
          <p className="text-sm text-muted-foreground">
            {filters.status || filters.search ? "No matching pipelines" : "No pipelines"}
          </p>
        </div>
      ) : (
        <div className="grid gap-3">
          {filteredPipelines.map((pipeline) => (
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
