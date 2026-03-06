"use client";

import { useState } from "react";
import { Plus, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";

const NODE_OPTIONS = [
  { type: "claude_agent", label: "Agent" },
  { type: "condition", label: "Condition" },
  { type: "end", label: "End" },
] as const;

interface ToolbarProps {
  onAddNode: (type: string) => void;
  onDeleteSelected: () => void;
  hasSelection: boolean;
}

export function Toolbar({ onAddNode, onDeleteSelected, hasSelection }: ToolbarProps) {
  const [open, setOpen] = useState(false);

  return (
    <div className="flex items-center gap-1 border-b border-border/50 px-3 py-1.5">
      <div className="relative">
        <Button
          variant="outline"
          size="sm"
          className="h-7 text-xs"
          onClick={() => setOpen(!open)}
        >
          <Plus className="mr-1 h-3.5 w-3.5" />
          Add Node
        </Button>
        {open && (
          <div className="absolute top-full left-0 z-50 mt-1 w-36 rounded-md border border-border bg-popover p-1 shadow-md">
            {NODE_OPTIONS.map((opt) => (
              <button
                key={opt.type}
                className="flex w-full items-center rounded-sm px-2 py-1.5 text-xs hover:bg-accent"
                onClick={() => {
                  onAddNode(opt.type);
                  setOpen(false);
                }}
              >
                {opt.label}
              </button>
            ))}
          </div>
        )}
      </div>

      {hasSelection && (
        <Button
          variant="ghost"
          size="sm"
          className="h-7 text-xs text-muted-foreground hover:text-destructive"
          onClick={onDeleteSelected}
        >
          <Trash2 className="mr-1 h-3.5 w-3.5" />
          Delete
        </Button>
      )}
    </div>
  );
}
