"use client";

import { useMemo } from "react";
import {
  ReactFlow,
  ReactFlowProvider,
  Background,
  Controls,
  type Node,
  type Edge,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { definitionToFlow } from "@/lib/template-flow";
import { autoLayout } from "@/lib/auto-layout";
import { StartNode } from "@/components/builder/start-node";
import { EndNode } from "@/components/builder/end-node";
import { FailedNode } from "@/components/builder/failed-node";
import { AgentNode } from "@/components/builder/agent-node";
import { ConditionNode } from "@/components/builder/condition-node";

const nodeTypes = {
  start: StartNode,
  end: EndNode,
  failed: FailedNode,
  claude_agent: AgentNode,
  condition: ConditionNode,
};

type NodeStatus = "pending" | "running" | "done" | "failed";

const statusStyles: Record<NodeStatus, React.CSSProperties> = {
  pending: {
    opacity: 0.5,
    filter: "grayscale(0.8)",
  },
  running: {
    boxShadow: "0 0 0 3px rgba(59, 130, 246, 0.5)",
    borderRadius: "8px",
  },
  done: {
    boxShadow: "0 0 0 3px rgba(34, 197, 94, 0.5)",
    borderRadius: "8px",
  },
  failed: {
    boxShadow: "0 0 0 3px rgba(239, 68, 68, 0.5)",
    borderRadius: "8px",
  },
};

interface PipelineGraphProps {
  definition: Record<string, unknown>;
  currentNodeId: string | null;
  completedNodeIds: string[];
  pipelineStatus: string;
}

function getNodeStatus(
  nodeId: string,
  currentNodeId: string | null,
  completedNodeIds: string[],
  pipelineStatus: string,
): NodeStatus {
  if (completedNodeIds.includes(nodeId)) return "done";
  if (pipelineStatus === "done" || pipelineStatus === "merged") return "done";
  if (nodeId === currentNodeId) {
    return pipelineStatus === "failed" ? "failed" : "running";
  }
  return "pending";
}

function PipelineGraphInner({
  definition,
  currentNodeId,
  completedNodeIds,
  pipelineStatus,
}: PipelineGraphProps) {
  const { nodes, edges } = useMemo(() => {
    const flow = definitionToFlow(definition as Parameters<typeof definitionToFlow>[0]);
    const needsLayout = flow.nodes.every(
      (n) => n.position.x === 0 && n.position.y === 0,
    );
    const laidOutNodes = needsLayout ? autoLayout(flow.nodes, flow.edges) : flow.nodes;
    return { nodes: laidOutNodes, edges: flow.edges };
  }, [definition]);

  const styledNodes: Node[] = useMemo(() => {
    return nodes.map((node) => {
      const status = getNodeStatus(node.id, currentNodeId, completedNodeIds, pipelineStatus);
      return {
        ...node,
        style: statusStyles[status],
      };
    });
  }, [nodes, currentNodeId, completedNodeIds, pipelineStatus]);

  const styledEdges: Edge[] = useMemo(() => {
    return edges.map((edge) => {
      const sourceStatus = getNodeStatus(edge.source, currentNodeId, completedNodeIds, pipelineStatus);
      const isDone = sourceStatus === "done";
      return {
        ...edge,
        style: {
          stroke: isDone ? "rgba(34, 197, 94, 0.6)" : undefined,
          strokeWidth: isDone ? 2 : undefined,
        },
        animated: edge.source === currentNodeId,
      };
    });
  }, [edges, currentNodeId, completedNodeIds, pipelineStatus]);

  return (
    <ReactFlow
      nodes={styledNodes}
      edges={styledEdges}
      nodeTypes={nodeTypes}
      nodesDraggable={false}
      nodesConnectable={false}
      elementsSelectable={false}
      panOnDrag
      zoomOnScroll
      fitView
      fitViewOptions={{ padding: 0.3 }}
      proOptions={{ hideAttribution: true }}
    >
      <Background />
      <Controls showInteractiveButton={false} />
    </ReactFlow>
  );
}

export function PipelineGraph(props: PipelineGraphProps) {
  return (
    <ReactFlowProvider>
      <PipelineGraphInner {...props} />
    </ReactFlowProvider>
  );
}
