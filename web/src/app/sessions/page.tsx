"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { Activity } from "lucide-react";
import { AppShell } from "@/components/app-shell";
import { SessionCard } from "@/components/session-card";
import { CreateSessionDialog } from "@/components/create-session-dialog";
import { useSessionsStore } from "@/store/sessions";
import { SkeletonList } from "@/components/skeleton-card";

function SessionsContent() {
  const {
    sessions,
    isLoading,
    fetchSessions,
    deleteSession,
    connectSSE,
    disconnectSSE,
  } = useSessionsStore();
  const router = useRouter();

  useEffect(() => {
    fetchSessions();
    connectSSE();
    return () => disconnectSSE();
  }, [fetchSessions, connectSSE, disconnectSSE]);

  return (
    <div className="p-6">
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-lg font-medium">Sessions</h2>
        <CreateSessionDialog
          onCreated={(key) => router.push(`/sessions/${key}`)}
        />
      </div>

      {isLoading && sessions.length === 0 ? (
        <SkeletonList count={4} />
      ) : sessions.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-20 text-center">
          <Activity className="mb-3 h-8 w-8 text-muted-foreground/50" />
          <p className="text-sm text-muted-foreground">No sessions</p>
        </div>
      ) : (
        <div className="grid gap-2">
          {sessions.map((session) => (
            <SessionCard
              key={session.session_key}
              session={session}
              onClick={() => router.push(`/sessions/${session.session_key}`)}
              onDelete={() => deleteSession(session.session_key)}
            />
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
