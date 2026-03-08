"use client";

import { Pause, Play, Trash2 } from "lucide-react";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import type { PipelineSchedule } from "@/store/schedules";
import { cronToHuman, formatNextRun } from "@/lib/cron-helpers";

export function ScheduleCard({
  schedule,
  onClick,
  onToggle,
  onDelete,
}: {
  schedule: PipelineSchedule;
  onClick?: () => void;
  onToggle: () => void;
  onDelete: () => void;
}) {
  const repoName = schedule.repo_path.split("/").pop() || schedule.repo_path;

  const scheduleDescription =
    schedule.schedule_type === "recurring" && schedule.cron_expression
      ? cronToHuman(schedule.cron_expression)
      : schedule.scheduled_at
        ? `Once: ${formatNextRun(schedule.scheduled_at, schedule.timezone)}`
        : schedule.schedule_type;

  return (
    <Card
      className={`border-border/50 bg-card/50 transition-colors hover:bg-accent/50 cursor-pointer ${
        !schedule.is_active ? "opacity-60" : ""
      }`}
      onClick={onClick}
    >
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <div className="flex-1 min-w-0 pr-2">
          <h3 className="text-sm font-medium truncate">{schedule.name}</h3>
        </div>
        <div className="flex items-center gap-1">
          <Badge variant="outline">{schedule.schedule_type}</Badge>
          <Badge variant={schedule.is_active ? "default" : "secondary"}>
            {schedule.is_active ? "Active" : "Paused"}
          </Badge>
          <Button
            variant="ghost"
            size="icon"
            className="h-7 w-7 text-muted-foreground hover:text-foreground"
            onClick={(e) => { e.stopPropagation(); onToggle(); }}
          >
            {schedule.is_active ? <Pause className="h-3.5 w-3.5" /> : <Play className="h-3.5 w-3.5" />}
          </Button>
          <Button
            variant="ghost"
            size="icon"
            className="h-7 w-7 text-muted-foreground hover:text-destructive"
            onClick={(e) => { e.stopPropagation(); onDelete(); }}
          >
            <Trash2 className="h-3.5 w-3.5" />
          </Button>
        </div>
      </CardHeader>
      <CardContent className="flex items-center gap-3 text-xs text-muted-foreground">
        <span>{repoName}</span>
        <span>{scheduleDescription}</span>
        {schedule.next_run_at && (
          <span>Next: {formatNextRun(schedule.next_run_at, schedule.timezone)}</span>
        )}
        {schedule.last_run_at && (
          <span>
            Last: {formatNextRun(schedule.last_run_at, schedule.timezone)}
            {schedule.last_run_status && ` \u2014 ${schedule.last_run_status}`}
          </span>
        )}
      </CardContent>
    </Card>
  );
}
