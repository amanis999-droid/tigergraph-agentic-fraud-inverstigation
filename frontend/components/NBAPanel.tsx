"use client";

import { useState } from "react";
import { NextBestActions } from "@/lib/types";
import { ApprovalBadge } from "./RiskBadge";
import { approveCase } from "@/lib/api";

export function NBAPanel({
  caseId,
  nba,
  initialStatus,
}: {
  caseId: string;
  nba: NextBestActions;
  initialStatus: "pending" | "approved" | "rejected";
}) {
  const [status, setStatus] = useState(initialStatus);
  const [loading, setLoading] = useState(false);

  async function handleApprove() {
    setLoading(true);
    try {
      await approveCase(caseId, true);
      setStatus("approved");
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  }

  const needsApproval = nba.final.approval_route !== "auto";

  return (
    <div className="bg-panel border border-border rounded mb-[18px]">
      <div className="px-[18px] py-3 border-b border-border text-xs font-semibold uppercase tracking-wide text-text-muted">
        Next Best Action
      </div>
      <div className="px-[18px] py-4 grid grid-cols-1 md:grid-cols-2 gap-3.5">
        <div className="bg-panel-raised border border-border rounded px-4 py-3.5">
          <div className="text-[11px] text-text-dim uppercase tracking-wide mb-2">Initial (before evidence)</div>
          <div className="font-mono text-[15px] font-bold mb-2">{nba.initial.action.replace(/_/g, " ")}</div>
          <ApprovalBadge route={nba.initial.approval_route} />
          <div className="text-text-muted text-[12.5px] leading-relaxed">{nba.initial.justification}</div>
        </div>
        <div className="bg-panel-raised border border-border rounded px-4 py-3.5">
          <div className="text-[11px] text-text-dim uppercase tracking-wide mb-2">Final (after evidence)</div>
          <div className="font-mono text-[15px] font-bold mb-2">{nba.final.action.replace(/_/g, " ")}</div>
          <ApprovalBadge route={nba.final.approval_route} />
          <div className="text-text-muted text-[12.5px] leading-relaxed">{nba.final.justification}</div>
          {needsApproval && (
            <button
              onClick={handleApprove}
              disabled={status !== "pending" || loading}
              className={`mt-3 px-4 py-2 rounded text-[12.5px] font-semibold font-sans ${
                status === "approved" ? "bg-risk-low text-bg" : "bg-text text-bg hover:opacity-85"
              } disabled:cursor-default`}
            >
              {loading ? "..." : status === "pending" ? "Approve action" : status === "approved" ? "✓ Approved" : "✕ Rejected"}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}