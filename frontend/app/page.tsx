"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { CaseSummary } from "@/lib/types";
import { fetchCases } from "@/lib/api";
import { RiskDot, VerdictBadge } from "@/components/RiskBadge";

function fmtMoney(n: number) {
  return "$" + n.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

export default function CaseListPage() {
  const [cases, setCases] = useState<CaseSummary[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchCases()
      .then(setCases)
      .catch((e) => setError(e.message));
  }, []);

  if (error) {
    return (
      <div className="p-9">
        <div className="text-risk-high text-sm">
          Could not reach the backend: {error}
          <div className="text-text-dim mt-2">
            Make sure the FastAPI server is running: <code className="font-mono">uvicorn main:app --reload --port 8000</code>
          </div>
        </div>
      </div>
    );
  }

  if (!cases) {
    return <div className="p-9 text-text-dim text-sm">Loading cases…</div>;
  }

  return (
    <div className="p-9 max-w-5xl">
      <h2 className="text-lg font-semibold mb-1">Cases</h2>
      <p className="text-text-dim text-sm mb-6">{cases.length} investigations</p>

      <div className="border border-border rounded overflow-hidden">
        {cases.map((c) => (
          <Link
            key={c.case_id}
            href={`/case/${c.case_id}`}
            className="flex items-center justify-between px-5 py-3.5 border-b border-border last:border-0 hover:bg-panel transition-colors"
          >
            <div className="flex items-center gap-4">
              <span className="font-mono text-sm font-semibold w-24">
                <RiskDot level={c.risk_level} />
                {c.case_id}
              </span>
              <span className="text-text-muted text-xs w-32">{c.trigger_type.replace(/_/g, " ")}</span>
              <span className="text-text-muted text-xs w-40">{c.fraud_pattern.replace(/_/g, " ")}</span>
              <span className="font-mono text-xs w-24">{fmtMoney(c.exposure_amount)}</span>
            </div>
            <div className="flex items-center gap-3">
              <span className="text-text-dim text-[11px] font-mono uppercase">{c.approval_status}</span>
              <VerdictBadge verdict={c.verdict} />
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
}