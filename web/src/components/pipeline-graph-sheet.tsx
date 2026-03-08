"use client";

import { useEffect, useMemo, useState } from "react";
import {
  ReactFlow,
  ReactFlowProvider,
  Background,
  Controls,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import {
  CheckCircle2,
  Loader2,
  AlertCircle,
  SkipForward,
  Circle,
} from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogTitle,
} from "@/components/ui/dialog";
import { apiFetch } from "@/lib/api";
import { definitionToFlow } from "@/lib/template-flow";
import { autoLayout } from "@/lib/auto-layout";
import { withStatusOverlay } from "@/components/builder/with-status-overlay";
import { AgentNode } from "@/components/builder/agent-node";
import { StartNode } from "@/components/builder/start-node";
import { EndNode } from "@/components/builder/end-node";
import { ConditionNode } from "@/components/builder/condition-node";
import { FailedNode } from "@/components/builder/failed-node";
import type { Pipeline, StepLog } from "@/store/pipelines";

const monitorNodeTypes = {
  start: withStatusOverlay(StartNode),
  end: withStatusOverlay(EndNode),
  failed: withStatusOverlay(FailedNode),
  claude_agent: withStatusOverlay(AgentNode),
  condition: withStatusOverlay(ConditionNode),
};

const stepStatusIcon = (status: string) => {
  switch (status) {
    case "completed":
      return <CheckCircle2 className="h-3.5 w-3.5 text-green-500 shrink-0" />;
    case "running":
      return <Loader2 className="h-3.5 w-3.5 animate-spin text-blue-500 shrink-0" />;
    case "failed":
      return <AlertCircle className="h-3.5 w-3.5 text-red-500 shrink-0" />;
    case "skipped":
      return <SkipForward className="h-3.5 w-3.5 text-muted-foreground shrink-0" />;
    default:
      return <Circle className="h-3 w-3 text-muted-foreground shrink-0" />;
  }
};

function StepEntry({ step }: { step: StepLog }) {
  return (
    <div className="flex items-start gap-2 py-1.5 border-b border-border/30 last:border-0">
      <div className="mt-0.5">{stepStatusIcon(step.status)}</div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-1.5">
          <span className="text-xs font-medium truncate">{step.node_name}</span>
          {step.duration_s != null && (
            <span className="text-[10px] text-muted-foreground ml-auto shrink-0">
              {step.duration_s < 60
                ? `${Math.round(step.duration_s)}s`
                : `${Math.floor(step.duration_s / 60)}m ${Math.round(step.duration_s % 60)}s`}
            </span>
          )}
        </div>
        {step.error && (
          <p className="text-[10px] text-red-500 mt-0.5 truncate">{step.error}</p>
        )}
      </div>
    </div>
  );
}

interface PipelineGraphSheetProps {
  pipeline: Pipeline;
  open: boolean;
  onClose: () => void;
}

export function PipelineGraphSheet({
  pipeline,
  open,
  onClose,
}: PipelineGraphSheetProps) {
  const [templateDef, setTemplateDef] = useState<{
    nodes: Array<{ id: string; type: string; [key: string]: unknown }>;
    edges: Array<{ from: string; to: string }>;
    version: number;
    name: string;
  } | null>(null);

  useEffect(() => {
    if (open && pipeline.template_id) {
      apiFetch(`/pipeline-templates/${pipeline.template_id}`)
        .then((res) => (res.ok ? res.json() : null))
        .then((data) => {
          if (data?.definition) setTemplateDef(data.definition);
        });
    }
  }, [open, pipeline.template_id]);

  const { nodes: rawNodes, edges: rawEdges } = useMemo(() => {
    if (!templateDef) return { nodes: [], edges: [] };
    return definitionToFlow(templateDef);
  }, [templateDef]);

  const layoutNodes = useMemo(
    () => (rawNodes.length > 0 ? autoLayout(rawNodes, rawEdges) : []),
    [rawNodes, rawEdges],
  );

  const statusMap = useMemo(() => {
    const map: Record<string, StepLog> = {};
    for (const step of pipeline.step_logs ?? []) {
      map[step.node_id] = step;
    }
    return map;
  }, [pipeline.step_logs]);

  const styledNodes = layoutNodes.map((n) => ({
    ...n,
    data: {
      ...n.data,
      __status: statusMap[n.id]?.status,
      __duration_s: statusMap[n.id]?.duration_s,
    },
  }));

  const styledEdges = rawEdges.map((e) => ({
    ...e,
    style:
      statusMap[e.source]?.status === "completed"
        ? { stroke: "rgb(34 197 94)", strokeWidth: 2 }
        : undefined,
    animated: statusMap[e.source]?.status === "running",
  }));

  return (
    <Dialog open={open} onOpenChange={(v) => !v && onClose()}>
      <DialogContent className="max-w-[95vw] sm:max-w-[95vw] h-[85vh] p-0">
        <DialogTitle className="sr-only">Execution Graph</DialogTitle>
        <div className="flex h-full">
          <div className="flex-1 relative">
            <ReactFlowProvider>
              <ReactFlow
                nodes={styledNodes}
                edges={styledEdges}
                nodeTypes={monitorNodeTypes}
                nodesDraggable={false}
                nodesConnectable={false}
                fitView
              >
                <Background />
                <Controls showInteractive={false} />
              </ReactFlow>
            </ReactFlowProvider>
          </div>
          <div className="w-72 border-l overflow-y-auto p-3">
            <h3 className="font-medium text-sm mb-2">Execution Log</h3>
            {(!pipeline.step_logs || pipeline.step_logs.length === 0) ? (
              <p className="text-xs text-muted-foreground">No steps yet</p>
            ) : (
              pipeline.step_logs.map((step, i) => (
                <StepEntry key={`${step.node_id}-${i}`} step={step} />
              ))
            )}
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
