"use client";

import type { NodeProps } from "@xyflow/react";
import { CheckCircle2, Loader2, AlertCircle } from "lucide-react";
import { formatDuration } from "@/lib/format-duration";

const statusClasses: Record<string, string> = {
  running: "ring-2 ring-blue-500 ring-offset-1 animate-pulse",
  completed: "ring-2 ring-green-500/50",
  failed: "ring-2 ring-red-500/50",
  skipped: "opacity-50",
};

export function withStatusOverlay(
  NodeComponent: React.ComponentType<NodeProps>,
) {
  return function MonitorNode(props: NodeProps) {
    const status = props.data.__status as string | undefined;
    const duration = props.data.__duration_s as number | undefined;

    return (
      <div
        className={`relative rounded-lg ${statusClasses[status ?? ""] ?? "opacity-40"}`}
      >
        <NodeComponent {...props} />
        {status === "completed" && (
          <CheckCircle2 className="absolute -top-1.5 -right-1.5 h-4 w-4 text-green-500 bg-background rounded-full" />
        )}
        {status === "running" && (
          <Loader2 className="absolute -top-1.5 -right-1.5 h-4 w-4 text-blue-500 animate-spin" />
        )}
        {status === "failed" && (
          <AlertCircle className="absolute -top-1.5 -right-1.5 h-4 w-4 text-red-500 bg-background rounded-full" />
        )}
        {duration != null && (
          <span className="absolute -bottom-5 left-1/2 -translate-x-1/2 text-[10px] text-muted-foreground whitespace-nowrap">
            {formatDuration(duration)}
          </span>
        )}
      </div>
    );
  };
}
