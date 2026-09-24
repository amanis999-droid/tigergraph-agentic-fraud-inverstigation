import { CaseSummary, CaseFull, CaseGraph } from "./types";

// Set NEXT_PUBLIC_API_URL in .env.local once the backend is deployed
// somewhere other than localhost. Defaults to the local FastAPI dev server.
const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export async function fetchCases(): Promise<CaseSummary[]> {
  const res = await fetch(`${API_BASE}/cases`, { cache: "no-store" });
  if (!res.ok) throw new Error(`Failed to fetch cases: ${res.status}`);
  return res.json();
}

export async function fetchCase(caseId: string): Promise<CaseFull> {
  const res = await fetch(`${API_BASE}/cases/${caseId}`, { cache: "no-store" });
  if (!res.ok) throw new Error(`Failed to fetch case ${caseId}: ${res.status}`);
  return res.json();
}

export async function fetchCaseGraph(caseId: string): Promise<CaseGraph> {
  const res = await fetch(`${API_BASE}/cases/${caseId}/graph`, { cache: "no-store" });
  if (!res.ok) throw new Error(`Failed to fetch graph for ${caseId}: ${res.status}`);
  return res.json();
}

export async function approveCase(caseId: string, approved: boolean): Promise<void> {
  const res = await fetch(`${API_BASE}/cases/${caseId}/approve`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ approved, approver: "analyst_demo" }),
  });
  if (!res.ok) throw new Error(`Failed to approve case ${caseId}: ${res.status}`);
}