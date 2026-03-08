"use client";

import { Cpu, FolderGit2, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import type { Session } from "@/store/sessions";

export function SessionCard({
  session,
  onClick,
  onDelete,
}: {
  session: Session;
  onClick: () => void;
  onDelete: () => void;
}) {
  const isBusy = session.status === "busy";
  const projectName = session.project_path?.split("/").pop() || "—";

  return (
    <div
      className={`group flex items-center gap-2 border-l-2 ${isBusy ? "border-l-red-500" : "border-l-green-500"} rounded-md border border-border/40 bg-card/50 px-3 py-2 transition-colors hover:bg-accent/50 cursor-pointer`}
      onClick={onClick}
    >
      {/* Status dot */}
      {isBusy ? (
        <span className="relative flex h-1.5 w-1.5 shrink-0">
          <span className="absolute inline-flex h-full w-full rounded-full bg-red-500 opacity-75 animate-ping" />
          <span className="relative inline-flex rounded-full h-1.5 w-1.5 bg-red-500" />
        </span>
      ) : (
        <span className="h-1.5 w-1.5 rounded-full bg-green-500 shrink-0" />
      )}

      {/* Name */}
      <span className="text-sm font-medium truncate">{session.name}</span>

      <div className="flex-1" />

      {/* Meta */}
      <span className="flex items-center gap-1 text-[11px] text-muted-foreground shrink-0">
        <FolderGit2 className="h-2.5 w-2.5" />
        {projectName}
      </span>
      <span className="flex items-center gap-1 text-[11px] text-muted-foreground shrink-0">
        <Cpu className="h-2.5 w-2.5" />
        {session.model || "—"}
      </span>
      <span
        className={`inline-flex items-center rounded-full px-1.5 py-0 text-[10px] font-medium shrink-0 ${
          isBusy ? "bg-red-500/15 text-red-500" : "bg-green-500/15 text-green-500"
        }`}
      >
        {session.status}
      </span>

      {/* Delete */}
      <Button
        variant="ghost"
        size="icon"
        className="h-6 w-6 text-muted-foreground opacity-0 group-hover:opacity-100 hover:text-destructive shrink-0"
        onClick={(e) => { e.stopPropagation(); onDelete(); }}
      >
        <Trash2 className="h-3 w-3" />
      </Button>
    </div>
  );
}
