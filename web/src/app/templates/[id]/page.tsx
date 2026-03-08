"use client";

import { useCallback, useEffect, useRef, useState, useMemo } from "react";
import { useParams, useRouter } from "next/navigation";
import {
  ReactFlow,
  ReactFlowProvider,
  Background,
  Controls,
  useNodesState,
  useEdgesState,
  useReactFlow,
  addEdge,
  type Connection,
  type Node,
  type Edge,
  type EdgeRemoveChange,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { ArrowLeft, Loader2, Save } from "lucide-react";
import { AppShell } from "@/components/app-shell";
import { Button } from "@/components/ui/button";
import { useTemplatesStore } from "@/store/templates";
import { apiFetch } from "@/lib/api";
import { definitionToFlow, flowToDefinition } from "@/lib/template-flow";
import { autoLayout } from "@/lib/auto-layout";
import { validateGraph, type ValidationError } from "@/lib/validate-graph";
import { StartNode } from "@/components/builder/start-node";
import { EndNode } from "@/components/builder/end-node";
import { FailedNode } from "@/components/builder/failed-node";
import { AgentNode } from "@/components/builder/agent-node";
import { ConditionNode } from "@/components/builder/condition-node";
import { ConfigPanel } from "@/components/builder/config-panel";
import { ContextPanel } from "@/components/builder/context-panel";
import { Toolbar } from "@/components/builder/toolbar";
import type { PipelineTemplate } from "@/store/templates";

function nextNodeId(type: string, nodes: Node[]): string {
  const prefix = `${type}_`;
  let max = 0;
  for (const n of nodes) {
    if (n.id.startsWith(prefix)) {
      const num = parseInt(n.id.slice(prefix.length), 10);
      if (num > max) max = num;
    }
  }
  return `${prefix}${max + 1}`;
}

const nodeTypes = {
  start: StartNode,
  end: EndNode,
  failed: FailedNode,
  claude_agent: AgentNode,
  condition: ConditionNode,
};

function BuilderContent() {
  const params = useParams();
  const router = useRouter();
  const { updateTemplate } = useTemplatesStore();
  const { screenToFlowPosition, fitView } = useReactFlow();
  const templateId = Number(params.id);

  const [template, setTemplate] = useState<PipelineTemplate | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [showContext, setShowContext] = useState(false);

  const [nodes, setNodes, onNodesChange] = useNodesState<Node>([]);
  const [edges, setEdges, onEdgesChangeBase] = useEdgesState<Edge>([]);

  /** Remove references to deletedIds from all nodes' target fields */
  const scrubNodeReferences = useCallback(
    (deletedIds: Set<string>) => {
      setNodes((nds) =>
        nds.map((node) => {
          const targets = node.data.targets as string[] | undefined;
          const branches = node.data.branches as { value: string; target: string }[] | undefined;
          const maxIterTarget = node.data.max_iterations_target as string | undefined;

          const hasTarget = targets?.some((t) => deletedIds.has(t));
          const hasBranch = branches?.some((b) => deletedIds.has(b.target));
          const hasMaxIter = maxIterTarget ? deletedIds.has(maxIterTarget) : false;

          if (!hasTarget && !hasBranch && !hasMaxIter) return node;

          const newData = { ...node.data };
          if (hasTarget) newData.targets = targets!.filter((t) => !deletedIds.has(t));
          if (hasBranch) newData.branches = branches!.filter((b) => !deletedIds.has(b.target));
          if (hasMaxIter) newData.max_iterations_target = "";
          return { ...node, data: newData };
        }),
      );
    },
    [setNodes],
  );

  const onEdgesChange = useCallback(
    (changes: Parameters<typeof onEdgesChangeBase>[0]) => {
      const removals = changes.filter((c): c is EdgeRemoveChange => c.type === "remove");
      if (removals.length > 0) {
        for (const removal of removals) {
          const edge = edges.find((e) => e.id === removal.id);
          if (edge) {
            const deletedTarget = edge.target;
            setNodes((nds) =>
              nds.map((node) => {
                if (node.id !== edge.source) return node;

                const targets = node.data.targets as string[] | undefined;
                const branches = node.data.branches as { value: string; target: string }[] | undefined;
                const maxIterTarget = node.data.max_iterations_target as string | undefined;

                const newData = { ...node.data };
                let changed = false;

                if (targets?.includes(deletedTarget)) {
                  newData.targets = targets.filter((t) => t !== deletedTarget);
                  changed = true;
                }
                if (branches?.some((b) => b.target === deletedTarget)) {
                  // If edge has a label, remove only the matching branch; otherwise remove all with that target
                  if (edge.label) {
                    newData.branches = branches.filter((b) => !(b.target === deletedTarget && b.value === edge.label));
                  } else {
                    newData.branches = branches.filter((b) => b.target !== deletedTarget);
                  }
                  changed = true;
                }
                if (maxIterTarget === deletedTarget) {
                  newData.max_iterations_target = "";
                  changed = true;
                }

                return changed ? { ...node, data: newData } : node;
              }),
            );
          }
        }
      }
      onEdgesChangeBase(changes);
    },
    [edges, onEdgesChangeBase, setNodes],
  );

  useEffect(() => {
    async function load() {
      const res = await apiFetch(`/pipeline-templates/${templateId}`);
      if (res.ok) {
        const data = await res.json();
        setTemplate(data);
        const flow = definitionToFlow(data.definition);
        setNodes(flow.nodes);
        setEdges(flow.edges);
      }
      setLoading(false);
    }
    load();
  }, [templateId, setNodes, setEdges]);

  const onConnect = useCallback(
    (connection: Connection) => {
      setEdges((eds) => addEdge({ ...connection, type: "smoothstep" }, eds));
      setNodes((nds) =>
        nds.map((node) => {
          if (node.id !== connection.source || !connection.target) return node;
          const type = node.type;
          if (type === "condition") {
            const branches = (node.data.branches as { value: string; target: string }[]) || [];
            if (branches.some((b) => b.target === connection.target)) return node;
            return { ...node, data: { ...node.data, branches: [...branches, { value: "", target: connection.target }] } };
          }
          if (type === "start" || type === "claude_agent" || type === "failed") {
            const targets = (node.data.targets as string[]) || [];
            if (targets.includes(connection.target)) return node;
            return { ...node, data: { ...node.data, targets: [...targets, connection.target] } };
          }
          return node;
        }),
      );
    },
    [setEdges, setNodes],
  );

  const onNodeClick = useCallback((_: React.MouseEvent, node: Node) => {
    setSelectedNodeId(node.id);
  }, []);

  const onPaneClick = useCallback(() => {
    setSelectedNodeId(null);
  }, []);

  const handleToggleContext = useCallback(() => {
    setShowContext((prev) => !prev);
  }, []);

  const handleNodeUpdate = useCallback(
    (id: string, data: Record<string, unknown>) => {
      setNodes((nds) =>
        nds.map((n) => (n.id === id ? { ...n, data } : n)),
      );

      // Sync edges from node data
      const syncEdges = (targets: { target: string; label?: string }[]) => {
        setEdges((eds) => {
          const otherEdges = eds.filter((e) => e.source !== id);
          const newEdges = targets
            .filter((t) => t.target)
            .map((t) => ({
              id: `${id}-${t.target}-${t.label || ""}`,
              source: id,
              target: t.target,
              type: "smoothstep" as const,
              label: t.label || undefined,
            }));
          return [...otherEdges, ...newEdges];
        });
      };

      if ((data.type === "start" || data.type === "claude_agent" || data.type === "failed") && Array.isArray(data.targets)) {
        syncEdges((data.targets as string[]).map((t) => ({ target: t })));
      }

      if (data.type === "condition" && Array.isArray(data.branches)) {
        const branches = data.branches as { value: string; target: string }[];
        const targets = branches.map((b) => ({ target: b.target, label: b.value }));
        const maxIterTarget = data.max_iterations_target as string | undefined;
        if (maxIterTarget) {
          targets.push({ target: maxIterTarget, label: "MAX_ROUNDS" });
        }
        syncEdges(targets);
      }
    },
    [setNodes, setEdges],
  );

  const handleAddNode = useCallback(
    (type: string) => {
      const id = nextNodeId(type, nodes);
      const defaults: Record<string, Record<string, unknown>> = {
        claude_agent: {
          id,
          type,
          name: "New Agent",
          prompt_template: "",
          model: null,
          timeout: 600,
          retry: { max_attempts: 1 },
          outputs: [],
          extract: {},
          status_label: "",
        },
        condition: {
          id,
          type,
          name: "New Condition",
          condition_field: "",
          branches: {},
        },
        end: { id, type, name: "Done", result_template: "" },
        failed: { id, type, name: "Failed", reason_template: "", targets: [] },
      };
      const newNode: Node = {
        id,
        type,
        position: screenToFlowPosition({ x: 200, y: 300 }),
        data: defaults[type] || { id, type },
      };
      setNodes((nds) => [...nds, newNode]);
      setSelectedNodeId(id);
    },
    [setNodes, nodes],
  );

  const handleDeleteSelected = useCallback(() => {
    if (!selectedNodeId) return;
    setNodes((nds) => nds.filter((n) => n.id !== selectedNodeId));
    setEdges((eds) =>
      eds.filter((e) => e.source !== selectedNodeId && e.target !== selectedNodeId),
    );
    scrubNodeReferences(new Set([selectedNodeId]));
    setSelectedNodeId(null);
  }, [selectedNodeId, setNodes, setEdges, scrubNodeReferences]);

  const handleAutoLayout = useCallback(() => {
    const laid = autoLayout(nodes, edges);
    setNodes(laid);
    setTimeout(() => fitView({ padding: 0.2 }), 50);
  }, [nodes, edges, setNodes, fitView]);

  const handleExportJson = useCallback(() => {
    if (!template) return;
    const definition = flowToDefinition(nodes, edges, {
      version: template.definition.version,
      name: template.definition.name,
    });
    const json = JSON.stringify(definition, null, 2);
    const blob = new Blob([json], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${template.name.replace(/\s+/g, "_").toLowerCase()}.json`;
    a.click();
    URL.revokeObjectURL(url);
  }, [template, nodes, edges]);

  // ── Compile ──────────────────────────────────────────────────────
  const [compileErrors, setCompileErrors] = useState<ValidationError[] | null>(null);
  const compileTimers = useRef<number[]>([]);

  const clearCompile = useCallback(() => {
    compileTimers.current.forEach(clearTimeout);
    compileTimers.current = [];
    setNodes((nds) => nds.map((n) => ({ ...n, className: undefined })));
    setEdges((eds) => eds.map((e) => ({ ...e, className: undefined })));
    setCompileErrors(null);
  }, [setNodes, setEdges]);

  const handleCompile = useCallback(() => {
    clearCompile();
    const result = validateGraph(nodes, edges);

    if (result.valid) {
      setCompileErrors(null);
      const order = result.traversalOrder;
      order.forEach((nodeId, i) => {
        const t = window.setTimeout(() => {
          setNodes((nds) =>
            nds.map((n) => (n.id === nodeId ? { ...n, className: "compile-valid" } : n)),
          );
          setEdges((eds) =>
            eds.map((e) => (e.source === nodeId ? { ...e, className: "compile-valid" } : e)),
          );
        }, i * 150);
        compileTimers.current.push(t);
      });
      // Clear after animation + hold
      const t = window.setTimeout(clearCompile, order.length * 150 + 3000);
      compileTimers.current.push(t);
    } else {
      setCompileErrors(result.errors);
      const errorIds = new Set(result.errors.map((e) => e.nodeId).filter(Boolean));
      setNodes((nds) =>
        nds.map((n) => ({ ...n, className: errorIds.has(n.id) ? "compile-error" : undefined })),
      );
      setEdges((eds) =>
        eds.map((e) => ({ ...e, className: errorIds.has(e.source) || errorIds.has(e.target) ? "compile-error" : undefined })),
      );
      const t = window.setTimeout(clearCompile, 5000);
      compileTimers.current.push(t);
    }
  }, [nodes, edges, setNodes, setEdges, clearCompile]);

  const selectedNode = nodes.find((n) => n.id === selectedNodeId) || null;

  const handleSave = useCallback(async () => {
    if (!template) return;
    setSaving(true);
    try {
      const definition = flowToDefinition(nodes, edges, {
        version: template.definition.version,
        name: template.definition.name,
      });
      await updateTemplate(templateId, { definition });
      setError("");
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Save failed";
      setError(msg);
      setTimeout(() => setError(""), 5000);
    }
    setSaving(false);
  }, [template, nodes, edges, templateId, updateTemplate]);

  // Autosave 5s after last change
  const initialLoad = useRef(true);
  useEffect(() => {
    if (initialLoad.current) {
      initialLoad.current = false;
      return;
    }
    if (!template) return;
    const timer = setTimeout(() => {
      handleSave();
    }, 5000);
    return () => clearTimeout(timer);
  }, [nodes, edges, template, handleSave]);

  if (loading) {
    return (
      <div className="flex h-full items-center justify-center">
        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (!template) {
    return (
      <div className="flex h-full flex-col items-center justify-center gap-2">
        <p className="text-sm text-muted-foreground">Template not found</p>
        <Button variant="ghost" size="sm" onClick={() => router.push("/templates")}>
          Back to templates
        </Button>
      </div>
    );
  }

  return (
    <div className="flex h-full flex-col">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-border/50 px-4 py-2">
        <div className="flex items-center gap-2">
          <Button variant="ghost" size="icon" className="h-8 w-8" onClick={() => router.push("/templates")}>
            <ArrowLeft className="h-4 w-4" />
          </Button>
          <h2 className="text-sm font-medium">{template.name}</h2>
          {error && <span className="text-xs text-destructive">{error}</span>}
        </div>
        <Button size="sm" onClick={handleSave} disabled={saving}>
          {saving ? <Loader2 className="mr-1 h-3.5 w-3.5 animate-spin" /> : <Save className="mr-1 h-3.5 w-3.5" />}
          Save
        </Button>
      </div>

      {/* Toolbar */}
      <Toolbar
        nodes={nodes}
        onAddNode={handleAddNode}
        onDeleteSelected={handleDeleteSelected}
        onAutoLayout={handleAutoLayout}
        onExportJson={handleExportJson}
        onCompile={handleCompile}
        onToggleContext={handleToggleContext}
        hasSelection={selectedNodeId !== null}
        showContext={showContext}
        compileErrors={compileErrors}
      />

      {/* Canvas + Config Panel */}
      <div className="flex flex-1 overflow-hidden">
        <div className="flex-1">
          <ReactFlow
            nodes={nodes}
            edges={edges}
            nodeTypes={nodeTypes}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onConnect={onConnect}
            onNodeClick={onNodeClick}
            onPaneClick={onPaneClick}
            fitView
            proOptions={{ hideAttribution: true }}
          >
            <Background />
            <Controls />
          </ReactFlow>
        </div>
        {selectedNode && (
          <ConfigPanel
            node={selectedNode}
            allNodes={nodes}
            onUpdate={handleNodeUpdate}
            onClose={() => setSelectedNodeId(null)}
          />
        )}
        {showContext && (
          <ContextPanel nodes={nodes} onClose={() => setShowContext(false)} />
        )}
      </div>
    </div>
  );
}

export default function BuilderPage() {
  return (
    <AppShell>
      <ReactFlowProvider>
        <BuilderContent />
      </ReactFlowProvider>
    </AppShell>
  );
}
