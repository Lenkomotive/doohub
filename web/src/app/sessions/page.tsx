"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { Activity } from "lucide-react";
import { Button } from "@/components/ui/button";
import { AppShell } from "@/components/app-shell";
import { SessionCard } from "@/components/session-card";
import { Swipeable } from "@/components/swipeable";
import { CreateSessionDialog } from "@/components/create-session-dialog";
import { useSessionsStore } from "@/store/sessions";
import { SkeletonList } from "@/components/skeleton-card";

const filters = [
  { label: "All", value: null },
  { label: "Busy", value: "busy" },
  { label: "Idle", value: "idle" },
];

function SessionsContent() {
  const { sessions, sessionsTotal, sessionFilter, isLoading, fetchSessions, setSessionFilter, deleteSession } =
    useSessionsStore();
  const router = useRouter();

  useEffect(() => {
    fetchSessions();
    const interval = setInterval(() => fetchSessions(sessionFilter), 5000);
    return () => clearInterval(interval);
  }, [fetchSessions, sessionFilter]);

  return (
    <div className="p-5 md:p-6">
      <div className="mb-4 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <h2 className="text-lg font-medium">Sessions</h2>
          <span className="text-sm text-muted-foreground">({sessionsTotal})</span>
        </div>
        <div className="flex items-center gap-1">
          <div className="flex gap-0.5">
            {filters.map((f) => (
              <Button
                key={f.label}
                variant={sessionFilter === f.value ? "secondary" : "ghost"}
                size="sm"
                onClick={() => setSessionFilter(f.value)}
              >
                {f.label}
              </Button>
            ))}
          </div>
          <CreateSessionDialog
            onCreated={(key) => router.push(`/sessions/${key}`)}
          />
        </div>
      </div>

      {isLoading && sessions.length === 0 ? (
        <SkeletonList count={4} />
      ) : sessions.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-20 text-center">
          <Activity className="mb-3 h-8 w-8 text-muted-foreground/50" />
          <p className="text-sm text-muted-foreground">No sessions</p>
        </div>
      ) : (
        <div className="grid gap-3">
          {sessions.map((session) => (
            <Swipeable key={session.session_key} onDelete={() => deleteSession(session.session_key)}>
              <SessionCard
                session={session}
                onClick={() => router.push(`/sessions/${session.session_key}`)}
              />
            </Swipeable>
          ))}
        </div>
      )}
    </div>
  );
}

export default function SessionsPage() {
  return (
    <AppShell>
      <SessionsContent />
    </AppShell>
  );
}
