"use client";

import { Cpu, FolderGit2, MessageSquare, Trash2 } from "lucide-react";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import type { Session } from "@/store/sessions";

const statusVariant: Record<string, "default" | "secondary" | "destructive" | "outline"> = {
  idle: "secondary",
  busy: "default",
  done: "outline",
  failed: "destructive",
};

export function SessionCard({
  session,
  onClick,
  onDelete,
}: {
  session: Session;
  onClick: () => void;
  onDelete: () => void;
}) {
  return (
    <Card
      className="cursor-pointer border-border/50 bg-card/50 transition-colors hover:bg-accent/50"
      onClick={onClick}
    >
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <h3 className="text-sm font-medium">{session.session_key}</h3>
        <div className="flex items-center gap-1">
          <Badge variant={statusVariant[session.status] || "secondary"}>
            {session.status}
          </Badge>
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
        {session.interactive && (
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <MessageSquare className="h-3 w-3" />
            interactive
          </div>
        )}
      </CardContent>
    </Card>
  );
}
