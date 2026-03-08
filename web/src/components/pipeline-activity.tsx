"use client";

import { useState } from "react";
import Markdown from "react-markdown";
import {
  CheckCircle2,
  Circle,
  AlertCircle,
  Loader2,
  Bot,
  GitFork,
  Play,
  Flag,
  SkipForward,
} from "lucide-react";
import type { StepLog } from "@/store/pipelines";

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

function formatDuration(s: number): string {
  return s < 60
    ? `${Math.round(s)}s`
    : `${Math.floor(s / 60)}m ${Math.round(s % 60)}s`;
}

interface PipelineActivityProps {
  steps: StepLog[];
  compact?: boolean;
}

export function PipelineActivity({ steps, compact }: PipelineActivityProps) {
  if (!steps || steps.length === 0) return null;

  return (
    <div className="space-y-0">
      {steps.map((step, i) => {
        const NodeIcon = stepNodeIcon[step.node_type] || Circle;
        return (
          <div
            key={`${step.node_id}-${i}`}
            className={`flex items-start gap-3 border-b border-border/30 last:border-0 ${compact ? "py-1.5 gap-2" : "py-2"}`}
          >
            <div className="mt-0.5 shrink-0">
              {compact ? (
                <span className="flex h-3.5 w-3.5 items-center justify-center">
                  {stepStatusIcon(step.status)}
                </span>
              ) : (
                stepStatusIcon(step.status)
              )}
            </div>
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2">
                {!compact && (
                  <NodeIcon className="h-3.5 w-3.5 text-muted-foreground shrink-0" />
                )}
                <span className={`font-medium truncate ${compact ? "text-xs" : "text-sm"}`}>
                  {step.node_name}
                </span>
                {!compact && (
                  <span className="text-xs text-muted-foreground">{step.node_type}</span>
                )}
                {step.duration_s != null && (
                  <span className="text-xs text-muted-foreground ml-auto shrink-0">
                    {formatDuration(step.duration_s)}
                  </span>
                )}
              </div>
              {!compact && step.output && <StepOutput text={step.output} />}
              {step.error && (
                <p className="text-xs text-destructive mt-1 truncate">{step.error}</p>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}
