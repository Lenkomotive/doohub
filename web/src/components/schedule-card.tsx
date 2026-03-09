"use client";

import { Clock, Pause, Play, Trash2, Repeat, Calendar } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import type { PipelineSchedule } from "@/store/schedules";

function formatNextRun(iso: string | null): string {
  if (!iso) return "—";
  const d = new Date(iso);
  const now = new Date();
  const diffMs = d.getTime() - now.getTime();
  if (diffMs < 0) return "overdue";
  if (diffMs < 60_000) return "< 1m";
  if (diffMs < 3600_000) return `in ${Math.round(diffMs / 60_000)}m`;
  if (diffMs < 86400_000) {
    const h = Math.floor(diffMs / 3600_000);
    const m = Math.round((diffMs % 3600_000) / 60_000);
    return `in ${h}h ${m}m`;
  }
  return d.toLocaleDateString(undefined, { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" });
}

function formatLastRun(iso: string | null): string {
  if (!iso) return "never";
  const d = new Date(iso);
  const diffMs = Date.now() - d.getTime();
  if (diffMs < 60_000) return "just now";
  if (diffMs < 3600_000) return `${Math.round(diffMs / 60_000)}m ago`;
  if (diffMs < 86400_000) return `${Math.floor(diffMs / 3600_000)}h ago`;
  return d.toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

export function ScheduleCard({
  schedule,
  onPause,
  onResume,
  onDelete,
}: {
  schedule: PipelineSchedule;
  onPause: () => void;
  onResume: () => void;
  onDelete: () => void;
}) {
  const repoName = schedule.repo_path.split("/").pop() || schedule.repo_path;

  return (
    <div
      className={`group border-l-2 ${schedule.is_active ? "border-l-green-500" : "border-l-zinc-500"} rounded-md border border-border/40 bg-card/50 px-3 py-2 transition-colors hover:bg-accent/50`}
    >
      {/* Line 1: Name + type badge + actions */}
      <div className="flex items-center gap-2 min-w-0">
        {schedule.is_active && (
          <span className="relative flex h-1.5 w-1.5 shrink-0">
            <span className="absolute inline-flex h-full w-full rounded-full opacity-75 animate-ping bg-green-500" />
            <span className="relative inline-flex rounded-full h-1.5 w-1.5 bg-green-500" />
          </span>
        )}
        <span className="text-sm font-medium truncate">{schedule.name}</span>
        <div className="flex-1" />
        <Badge variant={schedule.is_active ? "default" : "secondary"} className="text-[10px] h-5 shrink-0">
          {schedule.schedule_type === "recurring" ? (
            <><Repeat className="h-2.5 w-2.5 mr-0.5" />{schedule.cron_expression}</>
          ) : (
            <><Calendar className="h-2.5 w-2.5 mr-0.5" />once</>
          )}
        </Badge>
        {!schedule.is_active && (
          <Badge variant="secondary" className="text-[10px] h-5 shrink-0">paused</Badge>
        )}
        <div className="flex items-center shrink-0 opacity-0 group-hover:opacity-100 transition-opacity">
          {schedule.is_active ? (
            <Button variant="ghost" size="icon" className="h-6 w-6 text-muted-foreground hover:text-foreground" onClick={onPause} title="Pause">
              <Pause className="h-3 w-3" />
            </Button>
          ) : (
            <Button variant="ghost" size="icon" className="h-6 w-6 text-muted-foreground hover:text-foreground" onClick={onResume} title="Resume">
              <Play className="h-3 w-3" />
            </Button>
          )}
          <Button variant="ghost" size="icon" className="h-6 w-6 text-muted-foreground hover:text-destructive" onClick={onDelete}>
            <Trash2 className="h-3 w-3" />
          </Button>
        </div>
      </div>

      {/* Line 2: Meta */}
      <div className="flex items-center gap-2 mt-1 text-[11px] text-muted-foreground">
        <span>{repoName}</span>
        <span className="text-border">·</span>
        <span className="truncate max-w-[200px]">{schedule.task_description}</span>
        <div className="flex-1" />
        {schedule.run_count > 0 && (
          <>
            <span>{schedule.run_count} runs</span>
            <span className="text-border">·</span>
            <span>last {formatLastRun(schedule.last_run_at)}</span>
          </>
        )}
        {schedule.next_run_at && schedule.is_active && (
          <>
            <span className="text-border">·</span>
            <span className="flex items-center gap-0.5">
              <Clock className="h-2.5 w-2.5" />
              {formatNextRun(schedule.next_run_at)}
            </span>
          </>
        )}
      </div>
    </div>
  );
}
