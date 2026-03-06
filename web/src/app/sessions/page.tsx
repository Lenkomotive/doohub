"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { Activity } from "lucide-react";
import { Button } from "@/components/ui/button";
import { AppShell } from "@/components/app-shell";
import { SessionCard } from "@/components/session-card";
import { CreateSessionDialog } from "@/components/create-session-dialog";
import { useSessionsStore } from "@/store/sessions";
import { SkeletonList } from "@/components/skeleton-card";

function SessionsContent() {
  const { sessions, sessionFilter, isLoading, fetchSessions, setSessionFilter, deleteSession, connectSSE, disconnectSSE } =
    useSessionsStore();
  const router = useRouter();

  useEffect(() => {
    fetchSessions();
    connectSSE();
    return () => disconnectSSE();
  }, [fetchSessions, connectSSE, disconnectSSE]);

  const busyCount = sessions.filter((s) => s.status === "busy").length;
  const idleCount = sessions.filter((s) => s.status === "idle").length;

  const filters = [
    { label: "All", value: null, count: sessions.length },
    { label: "Busy", value: "busy" as const, count: busyCount },
    { label: "Idle", value: "idle" as const, count: idleCount },
  ];

  return (
    <div className="p-6">
      <div className="mb-4 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <h2 className="text-lg font-medium">Sessions</h2>
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
                {f.count > 0 && (
                  <span className="ml-1 text-xs text-muted-foreground">{f.count}</span>
                )}
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
            <div key={session.session_key} className="group">
              <SessionCard
                session={session}
                onClick={() => router.push(`/sessions/${session.session_key}`)}
                onDelete={() => deleteSession(session.session_key)}
              />
            </div>
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
