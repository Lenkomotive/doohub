"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { ArrowLeft, Clock, Loader2, Pause, Play, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { AppShell } from "@/components/app-shell";
import { PipelineCard } from "@/components/pipeline-card";
import { CreateScheduleDialog } from "@/components/create-schedule-dialog";
import { DeleteScheduleDialog } from "@/components/delete-schedule-dialog";
import { useSchedulesStore } from "@/store/schedules";
import { usePipelinesStore } from "@/store/pipelines";
import { cronToHuman, formatNextRun } from "@/lib/cron-helpers";

function ScheduleDetail() {
  const params = useParams();
  const router = useRouter();
  const scheduleId = Number(params.id);
  const [showDelete, setShowDelete] = useState(false);

  const {
    schedules, runs,
    fetchSchedules, fetchScheduleRuns,
    toggleSchedule, deleteSchedule,
    connectSSE, disconnectSSE,
  } = useSchedulesStore();

  const { mergeStatuses, checkMergeStatus, mergePipeline } = usePipelinesStore();

  useEffect(() => {
    fetchSchedules();
    fetchScheduleRuns(scheduleId);
    connectSSE();
    return () => disconnectSSE();
  }, [fetchSchedules, fetchScheduleRuns, scheduleId, connectSSE, disconnectSSE]);

  const schedule = schedules.find((s) => s.id === scheduleId);
  const scheduleRuns = runs[scheduleId] || [];

  const handleDelete = async () => {
    await deleteSchedule(scheduleId);
    router.push("/schedules");
  };

  if (schedules.length === 0) {
    return (
      <div className="flex h-full items-center justify-center">
        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (!schedule) {
    return (
      <div className="p-6">
        <Button variant="ghost" size="sm" onClick={() => router.push("/schedules")}>
          <ArrowLeft className="mr-2 h-4 w-4" />
          Back to schedules
        </Button>
        <div className="flex flex-col items-center justify-center py-20 text-center">
          <p className="text-sm text-muted-foreground">Schedule not found</p>
        </div>
      </div>
    );
  }

  const repoName = schedule.repo_path.split("/").pop() || schedule.repo_path;
  const scheduleDescription =
    schedule.schedule_type === "recurring" && schedule.cron_expression
      ? cronToHuman(schedule.cron_expression)
      : schedule.scheduled_at
        ? formatNextRun(schedule.scheduled_at, schedule.timezone)
        : "\u2014";

  return (
    <div className="p-6 max-w-3xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3 min-w-0">
          <Button
            variant="ghost"
            size="icon"
            className="h-8 w-8 shrink-0"
            onClick={() => router.push("/schedules")}
          >
            <ArrowLeft className="h-4 w-4" />
          </Button>
          <div className="min-w-0">
            <div className="flex items-center gap-2">
              <h1 className="text-lg font-medium truncate">{schedule.name}</h1>
              <Badge variant={schedule.is_active ? "default" : "secondary"}>
                {schedule.is_active ? "Active" : "Paused"}
              </Badge>
            </div>
          </div>
        </div>
        <div className="flex items-center gap-1 shrink-0">
          <Button
            variant="ghost"
            size="icon"
            className="h-8 w-8"
            onClick={() => toggleSchedule(scheduleId)}
          >
            {schedule.is_active ? <Pause className="h-4 w-4" /> : <Play className="h-4 w-4" />}
          </Button>
          <CreateScheduleDialog schedule={schedule} />
          <Button
            variant="ghost"
            size="icon"
            className="h-8 w-8 text-destructive"
            onClick={() => setShowDelete(true)}
          >
            <Trash2 className="h-4 w-4" />
          </Button>
        </div>
      </div>

      {/* Info */}
      <Card className="mb-4 border-border/50 bg-card/50">
        <CardContent className="pt-4">
          <div className="grid grid-cols-2 gap-3 text-sm">
            <div>
              <span className="text-muted-foreground">Repository</span>
              <p className="font-medium">{repoName}</p>
            </div>
            <div>
              <span className="text-muted-foreground">Model</span>
              <p className="font-medium">{schedule.model}</p>
            </div>
            <div>
              <span className="text-muted-foreground">Schedule</span>
              <p className="font-medium">{scheduleDescription}</p>
            </div>
            <div>
              <span className="text-muted-foreground">Type</span>
              <p className="font-medium capitalize">{schedule.schedule_type}</p>
            </div>
            {schedule.cron_expression && (
              <div>
                <span className="text-muted-foreground">Cron</span>
                <p className="font-medium font-mono text-xs">{schedule.cron_expression}</p>
              </div>
            )}
            <div>
              <span className="text-muted-foreground">Timezone</span>
              <p className="font-medium">{schedule.timezone}</p>
            </div>
            {schedule.issue_number && (
              <div>
                <span className="text-muted-foreground">Issue</span>
                <p className="font-medium">#{schedule.issue_number}</p>
              </div>
            )}
            {schedule.next_run_at && (
              <div>
                <span className="text-muted-foreground">Next run</span>
                <p className="font-medium">{formatNextRun(schedule.next_run_at, schedule.timezone)}</p>
              </div>
            )}
            {schedule.last_run_at && (
              <div>
                <span className="text-muted-foreground">Last run</span>
                <p className="font-medium">
                  {formatNextRun(schedule.last_run_at, schedule.timezone)}
                  {schedule.last_run_status && (
                    <span className="ml-2 text-xs text-muted-foreground">{schedule.last_run_status}</span>
                  )}
                </p>
              </div>
            )}
            <div>
              <span className="text-muted-foreground">Created</span>
              <p className="font-medium">{new Date(schedule.created_at).toLocaleString()}</p>
            </div>
          </div>
          {schedule.task_description && (
            <div className="mt-3 pt-3 border-t border-border/30">
              <span className="text-sm text-muted-foreground">Task</span>
              <p className="text-sm mt-1">{schedule.task_description}</p>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Runs */}
      <Card className="border-border/50 bg-card/50">
        <CardHeader className="pb-2">
          <div className="flex items-center gap-2">
            <Clock className="h-4 w-4 text-muted-foreground" />
            <h3 className="text-sm font-medium">Pipeline Runs</h3>
            <span className="text-xs text-muted-foreground">({scheduleRuns.length})</span>
          </div>
        </CardHeader>
        <CardContent>
          {scheduleRuns.length === 0 ? (
            <p className="text-sm text-muted-foreground py-4 text-center">No runs yet</p>
          ) : (
            <div className="space-y-2">
              {scheduleRuns.map((pipeline) => (
                <PipelineCard
                  key={pipeline.pipeline_key}
                  pipeline={pipeline}
                  mergeStatus={mergeStatuses[pipeline.pipeline_key]}
                  onClick={() => router.push(`/pipelines/${pipeline.pipeline_key}`)}
                  onCancel={() => {}}
                  onDelete={() => {}}
                  onCheckMergeStatus={() => checkMergeStatus(pipeline.pipeline_key)}
                  onMerge={() => mergePipeline(pipeline.pipeline_key)}
                />
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      <DeleteScheduleDialog
        scheduleName={schedule.name}
        open={showDelete}
        onOpenChange={setShowDelete}
        onConfirm={handleDelete}
      />
    </div>
  );
}

export default function ScheduleDetailPage() {
  return (
    <AppShell>
      <ScheduleDetail />
    </AppShell>
  );
}
