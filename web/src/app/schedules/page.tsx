"use client";

import { useEffect } from "react";
import { Clock } from "lucide-react";
import { AppShell } from "@/components/app-shell";
import { ScheduleCard } from "@/components/schedule-card";
import { CreateScheduleDialog } from "@/components/create-schedule-dialog";
import { useSchedulesStore } from "@/store/schedules";
import { SkeletonList } from "@/components/skeleton-card";

function SchedulesContent() {
  const {
    schedules, isLoading,
    fetchSchedules, pauseSchedule, resumeSchedule, deleteSchedule,
  } = useSchedulesStore();

  useEffect(() => {
    fetchSchedules();
  }, [fetchSchedules]);

  return (
    <div className="p-6">
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-lg font-medium">Schedules</h2>
        <CreateScheduleDialog />
      </div>

      {isLoading && schedules.length === 0 ? (
        <SkeletonList count={3} />
      ) : schedules.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-20 text-center">
          <Clock className="mb-3 h-8 w-8 text-muted-foreground/50" />
          <p className="text-sm text-muted-foreground">No schedules yet</p>
          <p className="mt-1 text-xs text-muted-foreground/70">Create one to run pipelines on a timer</p>
        </div>
      ) : (
        <div className="grid gap-2">
          {schedules.map((schedule) => (
            <ScheduleCard
              key={schedule.id}
              schedule={schedule}
              onPause={() => pauseSchedule(schedule.id)}
              onResume={() => resumeSchedule(schedule.id)}
              onDelete={() => deleteSchedule(schedule.id)}
            />
          ))}
        </div>
      )}
    </div>
  );
}

export default function SchedulesPage() {
  return (
    <AppShell>
      <SchedulesContent />
    </AppShell>
  );
}
