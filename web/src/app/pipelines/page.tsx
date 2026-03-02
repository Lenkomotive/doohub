"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { GitBranch } from "lucide-react";
import { Button } from "@/components/ui/button";
import { AppShell } from "@/components/app-shell";
import { PipelineCard } from "@/components/pipeline-card";
import { useSessionsStore } from "@/store/sessions";
import { SkeletonList } from "@/components/skeleton-card";

const filters = [
  { label: "All", value: null },
  { label: "Active", value: "active" },
  { label: "Done", value: "done" },
  { label: "Failed", value: "failed" },
];

function PipelinesContent() {
  const { pipelines, pipelinesTotal, pipelineFilter, isLoading, fetchPipelines, setPipelineFilter } =
    useSessionsStore();
  const router = useRouter();

  useEffect(() => {
    fetchPipelines();
    const interval = setInterval(() => fetchPipelines(pipelineFilter), 5000);
    return () => clearInterval(interval);
  }, [fetchPipelines, pipelineFilter]);

  return (
    <div className="p-5 md:p-6">
      <div className="mb-4 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <h2 className="text-lg font-medium">Pipelines</h2>
          <span className="text-sm text-muted-foreground">({pipelinesTotal})</span>
        </div>
        <div className="flex gap-1">
          {filters.map((f) => (
            <Button
              key={f.label}
              variant={pipelineFilter === f.value ? "secondary" : "ghost"}
              size="sm"
              onClick={() => setPipelineFilter(f.value)}
            >
              {f.label}
            </Button>
          ))}
        </div>
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
              key={pipeline.id}
              pipeline={pipeline}
              onClick={() => router.push(`/pipelines/${pipeline.id}`)}
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
