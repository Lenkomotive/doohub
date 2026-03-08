"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { CheckCircle2, AlertCircle } from "lucide-react";
import { apiFetch } from "@/lib/api";
import { usePipelinesStore } from "@/store/pipelines";

interface Summary {
  running: number;
  completed: number;
  failed: number;
  total: number;
}

export function MonitorBar() {
  const [summary, setSummary] = useState<Summary | null>(null);

  const fetchSummary = useCallback(async () => {
    try {
      const res = await apiFetch("/pipelines/summary");
      if (res.ok) setSummary(await res.json());
    } catch {
      // silently ignore fetch errors
    }
  }, []);

  // Poll every 30s
  useEffect(() => {
    fetchSummary();
    const id = setInterval(fetchSummary, 30_000);
    return () => clearInterval(id);
  }, [fetchSummary]);

  // Refetch when pipelines change via SSE
  const pipelines = usePipelinesStore((s) => s.pipelines);
  useEffect(() => {
    fetchSummary();
  }, [pipelines, fetchSummary]);

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
