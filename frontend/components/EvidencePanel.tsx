import { Evidence } from "@/lib/types";

export function EvidencePanel({ evidence }: { evidence: Evidence[] }) {
  return (
    <div className="bg-panel border border-border rounded mb-[18px]">
      <div className="px-[18px] py-3 border-b border-border text-xs font-semibold uppercase tracking-wide text-text-muted">
        Evidence ({evidence.length})
      </div>
      <div className="px-[18px] py-4">
        {evidence.map((e, i) => (
          <div key={i} className={`flex gap-3 py-2.5 ${i < evidence.length - 1 ? "border-b border-border" : ""}`}>
            <div className="font-mono text-[10px] text-text-dim bg-panel-raised px-[7px] py-0.5 rounded h-fit mt-0.5 whitespace-nowrap">
              {e.source.replace("_", " ")}
            </div>
            <div>
              <div className="font-semibold text-[13px]">{e.type.replace(/_/g, " ")}</div>
              <div className="text-text-muted text-[12.5px] mt-0.5">{e.description}</div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}