import { CaseFull } from "@/lib/types";

export function TimelinePanel({ data }: { data: CaseFull }) {
  const { case: c, next_best_actions, evidence_requests } = data;

  const steps = [
    { title: "Triggered", desc: `${c.trigger_type.replace(/_/g, " ")} on ${c.card_id}` },
    { title: "Evidence gathered", desc: `${c.evidence.length} items from graph, transaction history and device signals` },
    { title: "Risk assessed", desc: `${c.risk_level} risk · confidence ${(c.confidence * 100).toFixed(0)}%` },
    ...(evidence_requests.length
      ? [{ title: "Additional evidence requested", desc: `${evidence_requests.length} request(s) sent` }]
      : []),
    { title: "Action recommended", desc: `${next_best_actions.final.action.replace(/_/g, " ")} · ${next_best_actions.final.approval_route} approval` },
  ];

  return (
    <div className="bg-panel border border-border rounded mb-[18px]">
      <div className="px-[18px] py-3 border-b border-border text-xs font-semibold uppercase tracking-wide text-text-muted">
        Investigation timeline
      </div>
      <div className="px-[18px] py-4">
        <div className="relative pl-[22px]">
          <div className="absolute left-[5px] top-1 bottom-1 w-px bg-border" />
          {steps.map((s, i) => (
            <div key={i} className="relative pb-4.5 last:pb-0">
              <div
                className="absolute -left-[22px] top-[3px] w-[9px] h-[9px] rounded-full border-2"
                style={{ borderColor: "#4A9C7C", background: "#4A9C7C" }}
              />
              <div className="font-semibold text-[13px]">{s.title}</div>
              <div className="text-text-muted text-xs mt-0.5">{s.desc}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}