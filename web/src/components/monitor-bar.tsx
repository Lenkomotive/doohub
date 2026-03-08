"use client";

import Link from "next/link";
import { CheckCircle2, AlertCircle } from "lucide-react";
import { usePipelinesStore, isActive } from "@/store/pipelines";
import { useMemo } from "react";

export function MonitorBar() {
  const pipelines = usePipelinesStore((s) => s.pipelines);

  const summary = useMemo(() => {
    if (pipelines.length === 0) return null;
    let running = 0;
    let completed = 0;
    let failed = 0;
    for (const p of pipelines) {
      if (isActive(p.status)) running++;
      else if (p.status === "done" || p.status === "merged") completed++;
      else if (p.status === "failed") failed++;
    }
    return { running, completed, failed, total: pipelines.length };
  }, [pipelines]);

  if (!summary || summary.total === 0) return null;

  return (
    <div className="flex items-center gap-4 px-4 py-1 border-b bg-muted/30 text-xs">
      {summary.running > 0 && (
        <Link
          href="/pipelines?status=running"
          className="flex items-center gap-1.5 text-blue-600 hover:text-blue-700"
        >
          <span className="h-1.5 w-1.5 rounded-full bg-blue-500 animate-pulse" />
          {summary.running} running
        </Link>
      )}
      {summary.completed > 0 && (
        <Link
          href="/pipelines?status=completed"
          className="flex items-center gap-1.5 text-green-600 hover:text-green-700"
        >
          <CheckCircle2 className="h-3 w-3" />
          {summary.completed} completed
        </Link>
      )}
      {summary.failed > 0 && (
        <Link
          href="/pipelines?status=failed"
          className="flex items-center gap-1.5 text-red-600 hover:text-red-700"
        >
          <AlertCircle className="h-3 w-3" />
          {summary.failed} failed
        </Link>
      )}
      <span className="text-muted-foreground ml-auto">
        Total: {summary.total}
      </span>
    </div>
  );
}
