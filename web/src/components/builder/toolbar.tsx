"use client";

import { useEffect, useRef, useState } from "react";
import type { Node } from "@xyflow/react";
import { Braces, Download, LayoutGrid, Plus, Trash2, Zap } from "lucide-react";
import type { ValidationError } from "@/lib/validate-graph";
import { Button } from "@/components/ui/button";

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
  onCompile: () => void;
  onToggleContext: () => void;
  hasSelection: boolean;
  showContext: boolean;
  compileErrors?: ValidationError[] | null;
}

export function Toolbar({ nodes, onAddNode, onDeleteSelected, onAutoLayout, onExportJson, onCompile, onToggleContext, hasSelection, showContext, compileErrors }: ToolbarProps) {
  const [open, setOpen] = useState(false);
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
            onClick={onCompile}
          >
            <Zap className="mr-1 h-3.5 w-3.5" />
            Compile
          </Button>
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
            variant={showContext ? "secondary" : "ghost"}
            size="sm"
            className="h-7 text-xs"
            onClick={onToggleContext}
          >
            <Braces className="mr-1 h-3.5 w-3.5" />
            Context
          </Button>
        </div>
      </div>

      {compileErrors && compileErrors.length > 0 && (
        <div className="border-t border-red-500/30 bg-red-500/5 px-3 py-1.5">
          <div className="flex flex-wrap gap-x-4 gap-y-0.5">
            {compileErrors.map((e, i) => (
              <span key={i} className="text-[10px] text-red-500">
                {e.message}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
