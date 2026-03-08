"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Clock } from "lucide-react";
import { AppShell } from "@/components/app-shell";
import { ScheduleCard } from "@/components/schedule-card";
import { CreateScheduleDialog } from "@/components/create-schedule-dialog";
import { DeleteScheduleDialog } from "@/components/delete-schedule-dialog";
import { useSchedulesStore } from "@/store/schedules";
import { SkeletonList } from "@/components/skeleton-card";

function SchedulesContent() {
  const router = useRouter();
  const {
    schedules, isLoading,
    fetchSchedules, toggleSchedule, deleteSchedule,
    connectSSE, disconnectSSE,
  } = useSchedulesStore();

  const [deleteId, setDeleteId] = useState<number | null>(null);
  const deleteTarget = schedules.find((s) => s.id === deleteId);

  useEffect(() => {
    fetchSchedules();
    connectSSE();
    return () => disconnectSSE();
  }, [fetchSchedules, connectSSE, disconnectSSE]);

  const handleDelete = async () => {
    if (deleteId === null) return;
    await deleteSchedule(deleteId);
    setDeleteId(null);
  };

  return (
    <div className="p-6">
      <div className="mb-4 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <h2 className="text-lg font-medium">Schedules</h2>
          <span className="text-sm text-muted-foreground">({schedules.length})</span>
        </div>
        <CreateScheduleDialog />
      </div>

      {isLoading && schedules.length === 0 ? (
        <SkeletonList count={4} />
      ) : schedules.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-20 text-center">
          <Clock className="mb-3 h-8 w-8 text-muted-foreground/50" />
          <p className="text-sm text-muted-foreground">No schedules</p>
        </div>
      ) : (
        <div className="grid gap-3">
          {schedules.map((schedule) => (
            <ScheduleCard
              key={schedule.id}
              schedule={schedule}
              onClick={() => router.push(`/schedules/${schedule.id}`)}
              onToggle={() => toggleSchedule(schedule.id)}
              onDelete={() => setDeleteId(schedule.id)}
            />
          ))}
        </div>
      )}

      <DeleteScheduleDialog
        scheduleName={deleteTarget?.name || ""}
        open={deleteId !== null}
        onOpenChange={() => setDeleteId(null)}
        onConfirm={handleDelete}
      />
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
