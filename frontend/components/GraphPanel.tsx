"use client";

import { CaseGraph } from "@/lib/types";

const TYPE_COLOR: Record<string, string> = {
  customer: "#4A9C7C",
  card: "#E8E6E1",
  transaction: "#C99A3D",
  device: "#C9564A",
  prior_case: "#8B92A0",
};

export function GraphPanel({ graph }: { graph: CaseGraph }) {
  const width = 640;
  const height = Math.max(220, graph.nodes.length * 70);
  const centerX = width / 2;

  const positions: Record<string, { x: number; y: number }> = {};
  graph.nodes.forEach((n, i) => {
    const row = i;
    const isEven = row % 2 === 0;
    positions[n.id] = {
      x: isEven ? centerX - 160 : centerX + 160,
      y: 40 + row * 60,
    };
  });

  return (
    <div className="bg-panel border border-border rounded mb-[18px]">
      <div className="px-[18px] py-3 border-b border-border text-xs font-semibold uppercase tracking-wide text-text-muted">
        Graph relationships
      </div>
      <div className="px-[18px] py-4 overflow-x-auto">
        <svg width={width} height={height} className="min-w-[500px]">
          {graph.edges.map((e, i) => {
            const s = positions[e.source];
            const t = positions[e.target];
            if (!s || !t) return null;
            const midX = (s.x + t.x) / 2;
            const midY = (s.y + t.y) / 2;
            return (
              <g key={i}>
                <line x1={s.x} y1={s.y} x2={t.x} y2={t.y} stroke="#2A2F3A" strokeWidth={1.5} />
                <text x={midX} y={midY - 4} fill="#5C6270" fontSize={10} fontFamily="IBM Plex Mono, monospace" textAnchor="middle">
                  {e.label}
                </text>
              </g>
            );
          })}
          {graph.nodes.map((n) => {
            const p = positions[n.id];
            if (!p) return null;
            const color = TYPE_COLOR[n.type] || "#8B92A0";
            return (
              <g key={n.id}>
                <circle cx={p.x} cy={p.y} r={6} fill={color} />
                <text x={p.x + 12} y={p.y + 4} fill="#E8E6E1" fontSize={12} fontFamily="IBM Plex Mono, monospace">
                  {n.label}
                </text>
                <text x={p.x + 12} y={p.y + 17} fill="#5C6270" fontSize={9.5} fontFamily="IBM Plex Sans, sans-serif">
                  {n.type.replace("_", " ")}
                </text>
              </g>
            );
          })}
        </svg>
      </div>
    </div>
  );
}