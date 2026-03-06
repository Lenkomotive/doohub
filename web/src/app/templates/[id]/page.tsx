"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import {
  ReactFlow,
  Background,
  Controls,
  useNodesState,
  useEdgesState,
  addEdge,
  type Connection,
  type Node,
  type Edge,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { ArrowLeft, Loader2, Save } from "lucide-react";
import { AppShell } from "@/components/app-shell";
import { Button } from "@/components/ui/button";
import { useTemplatesStore } from "@/store/templates";
import { apiFetch } from "@/lib/api";
import { definitionToFlow, flowToDefinition } from "@/lib/template-flow";
import { StartNode } from "@/components/builder/start-node";
import { EndNode } from "@/components/builder/end-node";
import { AgentNode } from "@/components/builder/agent-node";
import { ConditionNode } from "@/components/builder/condition-node";
import { ConfigPanel } from "@/components/builder/config-panel";
import { Toolbar } from "@/components/builder/toolbar";
import type { PipelineTemplate } from "@/store/templates";

let nodeIdCounter = 0;

const nodeTypes = {
  start: StartNode,
  end: EndNode,
  claude_agent: AgentNode,
  condition: ConditionNode,
};

function BuilderContent() {
  const params = useParams();
  const router = useRouter();
  const { updateTemplate } = useTemplatesStore();
  const templateId = Number(params.id);

  const [template, setTemplate] = useState<PipelineTemplate | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);

  const [nodes, setNodes, onNodesChange] = useNodesState<Node>([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>([]);

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
    },
    [setEdges],
  );

  const onNodeClick = useCallback((_: React.MouseEvent, node: Node) => {
    setSelectedNodeId(node.id);
  }, []);

  const onPaneClick = useCallback(() => {
    setSelectedNodeId(null);
  }, []);

  const handleNodeUpdate = useCallback(
    (id: string, data: Record<string, unknown>) => {
      setNodes((nds) =>
        nds.map((n) => (n.id === id ? { ...n, data } : n)),
      );
    },
    [setNodes],
  );

  const handleAddNode = useCallback(
    (type: string) => {
      const id = `${type}_${++nodeIdCounter}`;
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
          default_branch: "",
          max_iterations: null,
        },
        end: { id, type, name: "End", status: "done" },
      };
      const newNode: Node = {
        id,
        type,
        position: { x: 250, y: 250 },
        data: defaults[type] || { id, type },
      };
      setNodes((nds) => [...nds, newNode]);
      setSelectedNodeId(id);
    },
    [setNodes],
  );

  const handleDeleteSelected = useCallback(() => {
    if (!selectedNodeId) return;
    setNodes((nds) => nds.filter((n) => n.id !== selectedNodeId));
    setEdges((eds) =>
      eds.filter((e) => e.source !== selectedNodeId && e.target !== selectedNodeId),
    );
    setSelectedNodeId(null);
  }, [selectedNodeId, setNodes, setEdges]);

  const selectedNode = nodes.find((n) => n.id === selectedNodeId) || null;

  const handleSave = useCallback(async () => {
    if (!template) return;
    setSaving(true);
    const definition = flowToDefinition(nodes, edges, {
      version: template.definition.version,
      name: template.definition.name,
    });
    await updateTemplate(templateId, { definition });
    setSaving(false);
  }, [template, nodes, edges, templateId, updateTemplate]);

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
        </div>
        <Button size="sm" onClick={handleSave} disabled={saving}>
          {saving ? <Loader2 className="mr-1 h-3.5 w-3.5 animate-spin" /> : <Save className="mr-1 h-3.5 w-3.5" />}
          Save
        </Button>
      </div>

      {/* Toolbar */}
      <Toolbar
        onAddNode={handleAddNode}
        onDeleteSelected={handleDeleteSelected}
        hasSelection={selectedNodeId !== null}
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
            onUpdate={handleNodeUpdate}
            onClose={() => setSelectedNodeId(null)}
          />
        )}
      </div>
    </div>
  );
}

export default function BuilderPage() {
  return (
    <AppShell>
      <BuilderContent />
    </AppShell>
  );
}
