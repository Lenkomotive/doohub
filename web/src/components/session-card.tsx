"use client";

import { Cpu, FolderGit2, Trash2 } from "lucide-react";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import type { Session } from "@/store/sessions";

const statusColor: Record<string, { bg: string; text: string }> = {
  busy: { bg: "bg-red-500/15", text: "text-red-500" },
  idle: { bg: "bg-green-500/15", text: "text-green-500" },
};

const defaultColor = { bg: "bg-muted", text: "text-muted-foreground" };

export function SessionCard({
  session,
  onClick,
  onDelete,
}: {
  session: Session;
  onClick: () => void;
  onDelete: () => void;
}) {
  const color = statusColor[session.status] || defaultColor;

  return (
    <Card
      className="cursor-pointer border-border/50 bg-card/50 transition-colors hover:bg-accent/50"
      onClick={onClick}
    >
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <h3 className="text-sm font-medium">{session.name}</h3>
        <div className="flex items-center gap-2">
          <span
            className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${color.bg} ${color.text}`}
          >
            {session.status}
          </span>
          <Button
            variant="ghost"
            size="icon"
            className="h-7 w-7 text-muted-foreground opacity-0 group-hover:opacity-100 hover:text-destructive"
            onClick={(e) => {
              e.stopPropagation();
              onDelete();
            }}
          >
            <Trash2 className="h-3.5 w-3.5" />
          </Button>
        </div>
      </CardHeader>
      <CardContent className="space-y-1">
        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          <Cpu className="h-3 w-3" />
          {session.model || "—"}
        </div>
        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          <FolderGit2 className="h-3 w-3" />
          {session.project_path?.split("/").pop() || "—"}
        </div>
      </CardContent>
    </Card>
  );
}
