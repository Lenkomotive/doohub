import type { Node, Edge } from "@xyflow/react";
import type { PipelineTemplate } from "@/store/templates";

/**
 * Convert a pipeline template definition into React Flow nodes and edges.
 */
export function definitionToFlow(definition: PipelineTemplate["definition"]): {
  nodes: Node[];
  edges: Edge[];
} {
  const nodes: Node[] = (definition.nodes || []).map((n) => ({
    id: n.id,
    type: n.type as string,
    position: (n.position as { x: number; y: number }) || { x: 0, y: 0 },
    data: { ...n },
  }));

  const edges: Edge[] = (definition.edges || []).map((e, i) => ({
    id: `e-${e.from}-${e.to}`,
    source: e.from,
    target: e.to,
    type: "smoothstep",
  }));

  return { nodes, edges };
}

/**
 * Convert React Flow state back to the pipeline template JSON schema.
 */
export function flowToDefinition(
  nodes: Node[],
  edges: Edge[],
  meta: { version: number; name: string },
): PipelineTemplate["definition"] {
  return {
    version: meta.version,
    name: meta.name,
    nodes: nodes.map((n) => ({
      ...n.data,
      id: n.id,
      type: String(n.type || n.data.type),
      position: n.position,
    })),
    edges: edges.map((e) => ({
      from: e.source,
      to: e.target,
    })),
  };
}
