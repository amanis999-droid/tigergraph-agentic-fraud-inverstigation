"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { CaseFull, CaseGraph } from "@/lib/types";
import { fetchCase, fetchCaseGraph } from "@/lib/api";
import { VerdictBadge } from "@/components/RiskBadge";
import { StatStrip } from "@/components/StatStrip";
import { EvidencePanel } from "@/components/EvidencePanel";
import { UncertaintyPanel } from "@/components/UncertaintyPanel";
import { NBAPanel } from "@/components/NBAPanel";
import { TimelinePanel } from "@/components/TimelinePanel";
import { GraphPanel } from "@/components/GraphPanel";

export default function CaseDetailPage() {
  const params = useParams();
  const caseId = params.id as string;

  const [data, setData] = useState<CaseFull | null>(null);
  const [graph, setGraph] = useState<CaseGraph | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([fetchCase(caseId), fetchCaseGraph(caseId)])
      .then(([caseData, graphData]) => {
        setData(caseData);
        setGraph(graphData);
      })
      .catch((e) => setError(e.message));
  }, [caseId]);

  if (error) {
    return (
      <div className="p-9">
        <div className="text-risk-high text-sm">Could not load case: {error}</div>
      </div>
    );
  }

  if (!data) {
    return <div className="p-9 text-text-dim text-sm">Loading case…</div>;
  }

  const c = data.case;

  return (
    <div className="p-9 max-w-4xl">
      <Link href="/" className="text-text-dim text-xs hover:text-text-muted mb-5 inline-block">
        ← All cases
      </Link>

      <div className="flex justify-between items-start gap-5 flex-wrap mb-5.5">
        <div>
          <h2 className="font-mono text-[22px]">{c.case_id}</h2>
          <div className="text-text-muted text-[13px] mt-1.5">
            {c.fraud_pattern.replace(/_/g, " ")} pattern · triggered by {c.trigger_type.replace(/_/g, " ")}
          </div>
        </div>
        <VerdictBadge verdict={c.verdict} />
      </div>

      <StatStrip data={data} />

      <div className="bg-panel border border-border rounded mb-[18px]">
        <div className="px-[18px] py-3 border-b border-border text-xs font-semibold uppercase tracking-wide text-text-muted">
          Reasoning
        </div>
        <div className="px-[18px] py-4 text-[13.5px] leading-relaxed">{c.reasoning}</div>
      </div>

      <EvidencePanel evidence={c.evidence} />

      {graph && <GraphPanel graph={graph} />}

      <UncertaintyPanel evidenceRequests={data.evidence_requests} stopReason={data.stop_reason} />

      <NBAPanel caseId={c.case_id} nba={data.next_best_actions} initialStatus={c.approval_status || "pending"} />

      {c.similar_past_cases.length > 0 && (
        <div className="bg-panel border border-border rounded mb-[18px]">
          <div className="px-[18px] py-3 border-b border-border text-xs font-semibold uppercase tracking-wide text-text-muted">
            Similar past cases
          </div>
          <div className="px-[18px] py-4">
            {c.similar_past_cases.map((id) => (
              <span key={id} className="inline-block font-mono text-[11.5px] bg-panel-raised border border-border px-2.5 py-1 rounded mr-1.5 mb-1.5 text-text-muted">
                {id}
              </span>
            ))}
          </div>
        </div>
      )}

      <TimelinePanel data={data} />
    </div>
  );
}