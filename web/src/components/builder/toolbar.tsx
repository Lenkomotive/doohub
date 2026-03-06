"use client";

import { useEffect, useRef, useState } from "react";
import type { Node } from "@xyflow/react";
import { Braces, Plus, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";

const NODE_OPTIONS = [
  { type: "claude_agent", label: "Agent" },
  { type: "condition", label: "Condition" },
  { type: "end", label: "End" },
] as const;

interface ToolbarProps {
  nodes: Node[];
  onAddNode: (type: string) => void;
  onDeleteSelected: () => void;
  hasSelection: boolean;
}

export function Toolbar({ nodes, onAddNode, onDeleteSelected, hasSelection }: ToolbarProps) {
  const [open, setOpen] = useState(false);
  const [showCtx, setShowCtx] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    function handleClick(e: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as HTMLElement)) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, [open]);

  const ctxEntries = nodes
    .filter((n) => n.type === "claude_agent")
    .map((n) => ({
      name: (n.data.name as string) || n.id,
      outputs: (n.data.outputs as string[]) || [],
      extractFields: Object.keys((n.data.extract as Record<string, string>) || {}),
    }))
    .filter((e) => e.outputs.length > 0 || e.extractFields.length > 0);

  return (
    <div className="border-b border-border/50">
      <div className="flex items-center gap-1 px-3 py-1.5">
        <div className="relative" ref={dropdownRef}>
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

        <div className="ml-auto">
          <Button
            variant={showCtx ? "secondary" : "ghost"}
            size="sm"
            className="h-7 text-xs"
            onClick={() => setShowCtx(!showCtx)}
          >
            <Braces className="mr-1 h-3.5 w-3.5" />
            Context
          </Button>
        </div>
      </div>

      {showCtx && (
        <div className="border-t border-border/50 px-3 py-2">
          {ctxEntries.length === 0 ? (
            <p className="text-[10px] text-muted-foreground">
              No outputs defined yet. Add outputs to agent nodes to see available variables.
            </p>
          ) : (
            <div className="flex flex-wrap gap-x-4 gap-y-1.5">
              {ctxEntries.map((entry) => (
                <div key={entry.name} className="flex items-center gap-1.5">
                  <span className="text-[10px] text-muted-foreground">{entry.name}:</span>
                  {[...entry.outputs, ...entry.extractFields].map((v) => (
                    <Badge key={v} variant="outline" className="text-[9px] px-1 py-0 font-mono">
                      {`{{${v}}}`}
                    </Badge>
                  ))}
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
