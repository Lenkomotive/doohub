"use client";

import type { Node } from "@xyflow/react";
import { Braces, X } from "lucide-react";
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

export function ContextPanel({
  nodes,
  onClose,
}: {
  nodes: Node[];
  onClose: () => void;
}) {
  const usedPipelineVars = PIPELINE_VARS.filter((v) =>
    nodes.some(
      (n) =>
        n.type === "claude_agent" &&
        ((n.data.prompt_template as string) || "").includes(`{{${v}}}`),
    ),
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
    <div className="w-72 border-l border-border/50 overflow-y-auto">
      <div className="flex items-center justify-between px-3 py-2 border-b border-border/50">
        <div className="flex items-center gap-1.5">
          <Braces className="h-3.5 w-3.5 text-muted-foreground" />
          <span className="text-xs font-medium">Context Variables</span>
        </div>
        <Button variant="ghost" size="icon" className="h-6 w-6" onClick={onClose}>
          <X className="h-3.5 w-3.5" />
        </Button>
      </div>

      <div className="p-3 space-y-4">
        <div>
          <span className="text-[10px] font-medium text-muted-foreground uppercase tracking-wider">
            Pipeline
          </span>
          {usedPipelineVars.length > 0 ? (
            <div className="flex flex-wrap gap-1 mt-1.5">
              {usedPipelineVars.map((v) => (
                <Badge key={v} variant="outline" className="text-[9px] px-1.5 py-0 font-mono">
                  {`{{${v}}}`}
                </Badge>
              ))}
            </div>
          ) : (
            <p className="text-[10px] text-muted-foreground mt-1">
              No pipeline vars used in prompts yet.
            </p>
          )}
        </div>

        {ctxEntries.length > 0 && (
          <div>
            <span className="text-[10px] font-medium text-muted-foreground uppercase tracking-wider">
              Agent Outputs
            </span>
            <div className="mt-1.5 space-y-2">
              {ctxEntries.map((entry) => (
                <div key={entry.name}>
                  <span className="text-[10px] text-muted-foreground">{entry.name}</span>
                  <div className="flex flex-wrap gap-1 mt-0.5">
                    {entry.outputs.map((v) => (
                      <Badge key={v} variant="outline" className="text-[9px] px-1.5 py-0 font-mono">
                        {`{{${v}}}`}
                      </Badge>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {usedPipelineVars.length === 0 && ctxEntries.length === 0 && (
          <p className="text-[10px] text-muted-foreground">
            Add pipeline vars to prompts or outputs to agents to see them here.
          </p>
        )}
      </div>
    </div>
  );
}
