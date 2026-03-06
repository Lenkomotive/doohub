"use client";

import { useEffect, useRef, useState } from "react";
import type { Node } from "@xyflow/react";
import { Braces, Download, LayoutGrid, Plus, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";

const PIPELINE_VARS = [
  "issue_number",
  "issue_title",
  "issue_body",
  "repo_path",
  "branch",
  "model",
];

const NODE_OPTIONS = [
  { type: "claude_agent", label: "Agent" },
  { type: "condition", label: "Condition" },
  { type: "end", label: "Done" },
  { type: "failed", label: "Failed" },
] as const;

interface ToolbarProps {
  nodes: Node[];
  onAddNode: (type: string) => void;
  onDeleteSelected: () => void;
  onAutoLayout: () => void;
  onExportJson: () => void;
  hasSelection: boolean;
}

export function Toolbar({ nodes, onAddNode, onDeleteSelected, onAutoLayout, onExportJson, hasSelection }: ToolbarProps) {
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

  // Collect pipeline vars actually referenced in prompt templates
  const usedPipelineVars = PIPELINE_VARS.filter((v) =>
    nodes.some((n) =>
      n.type === "claude_agent" &&
      ((n.data.prompt_template as string) || "").includes(`{{${v}}}`)
    )
  );

  const ctxEntries = nodes
    .filter((n) => n.type === "claude_agent")
    .map((n) => ({
      name: (n.data.name as string) || n.id,
      outputs: ((n.data.outputs as { name: string }[]) || [])
        .map((o) => o.name)
        .filter(Boolean),
    }))
    .filter((e) => e.outputs.length > 0);

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

        <div className="ml-auto flex items-center gap-1">
          <Button
            variant="ghost"
            size="sm"
            className="h-7 text-xs"
            onClick={onAutoLayout}
          >
            <LayoutGrid className="mr-1 h-3.5 w-3.5" />
            Arrange
          </Button>
          <Button
            variant="ghost"
            size="sm"
            className="h-7 text-xs"
            onClick={onExportJson}
          >
            <Download className="mr-1 h-3.5 w-3.5" />
            Export
          </Button>
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
        <div className="border-t border-border/50 px-3 py-2 space-y-2">
          {usedPipelineVars.length > 0 && (
            <div>
              <span className="text-[10px] text-muted-foreground">Pipeline:</span>
              <div className="flex flex-wrap gap-1 mt-1">
                {usedPipelineVars.map((v) => (
                  <Badge key={v} variant="outline" className="text-[9px] px-1 py-0 font-mono">
                    {`{{${v}}}`}
                  </Badge>
                ))}
              </div>
            </div>
          )}
          {ctxEntries.length > 0 && (
            <div className="flex flex-wrap gap-x-4 gap-y-1.5">
              {ctxEntries.map((entry) => (
                <div key={entry.name}>
                  <span className="text-[10px] text-muted-foreground">{entry.name}:</span>
                  <div className="flex flex-wrap gap-1 mt-1">
                    {entry.outputs.map((v) => (
                      <Badge key={v} variant="outline" className="text-[9px] px-1 py-0 font-mono">
                        {`{{${v}}}`}
                      </Badge>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          )}
          {usedPipelineVars.length === 0 && ctxEntries.length === 0 && (
            <p className="text-[10px] text-muted-foreground">
              No variables in context yet. Add pipeline vars to prompts or outputs to agents.
            </p>
          )}
        </div>
      )}
    </div>
  );
}
