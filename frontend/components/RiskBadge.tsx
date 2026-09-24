import { RiskLevel } from "@/lib/types";

const RISK_COLOR: Record<RiskLevel, string> = {
  high: "bg-risk-high text-risk-high",
  medium: "bg-risk-medium text-risk-medium",
  low: "bg-risk-low text-risk-low",
};

export function RiskDot({ level }: { level: RiskLevel }) {
  return (
    <span
      className="inline-block w-[7px] h-[7px] rounded-full mr-2 align-middle"
      style={{ background: level === "high" ? "#C9564A" : level === "medium" ? "#C99A3D" : "#4A9C7C" }}
    />
  );
}

const VERDICT_STYLE: Record<string, string> = {
  fraud: "bg-risk-high/10 text-risk-high",
  not_fraud: "bg-risk-low/10 text-risk-low",
  uncertain: "bg-risk-medium/10 text-risk-medium",
};

export function VerdictBadge({ verdict }: { verdict: string }) {
  return (
    <span
      className={`px-3 py-1.5 rounded text-xs font-mono font-semibold uppercase tracking-wide whitespace-nowrap ${VERDICT_STYLE[verdict] || ""}`}
    >
      {verdict.replace("_", " ")}
    </span>
  );
}

const APPROVAL_STYLE: Record<string, string> = {
  auto: "bg-risk-low/15 text-risk-low",
  L1: "bg-risk-medium/15 text-risk-medium",
  L2: "bg-risk-high/15 text-risk-high",
};

export function ApprovalBadge({ route }: { route: string }) {
  return (
    <span className={`inline-block font-mono text-[10.5px] font-semibold px-2 py-1 rounded mb-2 ${APPROVAL_STYLE[route] || ""}`}>
      {route} approval
    </span>
  );
}