import type { Node, Edge } from "@xyflow/react";
import type { PipelineTemplate } from "@/store/templates";

/**
 * Convert a pipeline template definition into React Flow nodes and edges.
 */
export function definitionToFlow(definition: PipelineTemplate["definition"]): {
  nodes: Node[];
  edges: Edge[];
} {
  const defEdges = definition.edges || [];

  // Build source → targets map so node data stays in sync with edges
  const edgesBySource: Record<string, string[]> = {};
  for (const e of defEdges) {
    (edgesBySource[e.from] ||= []).push(e.to);
  }

  const nodes: Node[] = (definition.nodes || []).map((n) => {
    const data = { ...n };
    // Populate targets from edges so syncEdges in the builder doesn't wipe them
    if (["start", "claude_agent", "end", "failed"].includes(n.type)) {
      if (!Array.isArray(data.targets) || data.targets.length === 0) {
        data.targets = edgesBySource[n.id] || [];
      }
    }
    return {
      id: n.id,
      type: n.type as string,
      position: (n.position as { x: number; y: number }) || { x: 0, y: 0 },
      data,
    };
  });

  // Build condition branch labels: source+target → label
  const branchLabels: Record<string, string> = {};
  const nodeMap: Record<string, (typeof definition.nodes)[number]> = {};
  for (const n of definition.nodes || []) nodeMap[n.id] = n;
  for (const n of definition.nodes || []) {
    if (n.type !== "condition") continue;
    const branches = n.branches;
    if (Array.isArray(branches)) {
      for (const b of branches as { value: string; target: string }[]) {
        if (b.value && b.target) branchLabels[`${n.id}-${b.target}`] = b.value;
      }
    } else if (branches && typeof branches === "object") {
      for (const [value, target] of Object.entries(branches as Record<string, string>)) {
        branchLabels[`${n.id}-${target}`] = value;
      }
    }
    if (n.max_iterations_target) {
      branchLabels[`${n.id}-${n.max_iterations_target}`] = "MAX_ROUNDS";
    }
  }

  const edges: Edge[] = defEdges.map((e) => ({
    id: `e-${e.from}-${e.to}`,
    source: e.from,
    target: e.to,
    type: "smoothstep",
    label: branchLabels[`${e.from}-${e.to}`] || undefined,
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
