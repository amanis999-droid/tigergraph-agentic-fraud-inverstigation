export type Verdict = "fraud" | "not_fraud" | "uncertain";
export type RiskLevel = "low" | "medium" | "high";
export type ApprovalRoute = "auto" | "L1" | "L2";

export interface Evidence {
  type: string;
  description: string;
  source: string;
}

export interface CaseSummary {
  case_id: string;
  trigger_type: string;
  verdict: Verdict;
  risk_level: RiskLevel;
  fraud_pattern: string;
  exposure_amount: number;
  approval_status: "pending" | "approved" | "rejected";
}

export interface CaseRecord {
  case_id: string;
  trigger_type: string;
  customer_id: string;
  card_id: string;
  flagged_transaction_id: string;
  verdict: Verdict;
  fraud_pattern: string;
  risk_level: RiskLevel;
  confidence: number;
  exposure_amount: number;
  evidence: Evidence[];
  similar_past_cases: string[];
  reasoning: string;
  approval_status?: "pending" | "approved" | "rejected";
}

export interface SAR {
  required: boolean;
  reason: string;
  summary: string;
}

export interface NBAEntry {
  action: string;
  approval_route: ApprovalRoute;
  justification: string;
}

export interface NextBestActions {
  initial: NBAEntry;
  final: NBAEntry;
}

export interface CaseFull {
  case: CaseRecord;
  sar: SAR;
  next_best_actions: NextBestActions;
  evidence_requests: string[];
  stop_reason: string;
  tool_calls: string[];
  tokens: number;
  latency_s: number;
}

export interface GraphNode {
  id: string;
  label: string;
  type: "customer" | "card" | "transaction" | "device" | "prior_case";
}

export interface GraphEdge {
  source: string;
  target: string;
  label: string;
}

export interface CaseGraph {
  case_id: string;
  nodes: GraphNode[];
  edges: GraphEdge[];
}