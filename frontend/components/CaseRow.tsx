"use client";

import Link from "next/link";
import { CaseSummary } from "@/lib/types";
import { RiskDot } from "./RiskBadge";

function fmtMoney(n: number) {
  return "$" + n.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

export function CaseRow({ c, active }: { c: CaseSummary; active: boolean }) {
  return (
    <Link
      href={`/case/${c.case_id}`}
      className={`block px-[18px] py-3.5 border-b border-border hover:bg-panel transition-colors ${
        active ? "bg-panel-raised border-l-2 border-l-text pl-4" : ""
      }`}
    >
      <div className="font-mono text-[13px] font-semibold">
        <RiskDot level={c.risk_level} />
        {c.case_id}
      </div>
      <div className="text-text-dim text-xs mt-1">
        {c.trigger_type.replace("_", " ")} · {c.verdict.replace("_", " ")} · {fmtMoney(c.exposure_amount)}
      </div>
    </Link>
  );
}