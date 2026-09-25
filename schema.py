from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class CaseInput(BaseModel):
    case_id: str
    trigger_text: str
    flagged_txn_id: str
    card_id: str
    customer_id: str
    risk_score: float | None = None


class EvidenceForPolicy(BaseModel):
    claim: str
    source: Literal["graph", "document", "customer", "external"]
    signals: list[str] = Field(default_factory=list)
    entity_ids: list[str] = Field(default_factory=list)
    ref: str = ""


class Evidence(BaseModel):
    claim: str
    source: Literal["graph", "document", "customer", "external"]
    ref: str
    entity_ids: list[str] = Field(default_factory=list)


class EvidenceRequest(BaseModel):
    type: Literal["customer_validation", "step_up_auth", "analyst_info"]
    asked_after_step: int
    assumed_response: str = ""


class RecommendedAction(BaseModel):
    action: str
    route: Literal["auto", "L1", "L2"]
    reason: str


class NextBestActions(BaseModel):
    initial: list[RecommendedAction] = Field(default_factory=list)
    final: list[RecommendedAction] = Field(default_factory=list)
    what_changed: str = "nothing"


class Sar(BaseModel):
    file: bool = False
    reason: str = ""
    narrative: str = ""
    subjects: list[str] = Field(default_factory=list)
    total_amount_usd: float = 0.0
    activity_dates: list[str] = Field(default_factory=list)


class CaseRecord(BaseModel):
    status: Literal["open", "closed_fraud", "closed_legitimate", "escalated"]
    verdict: Literal["fraud", "legitimate", "uncertain"]
    fraud_probability: float = 0.0
    pattern: Literal[
        "card_testing",
        "card_not_present_fraud",
        "card_not_present_new_device",
        "out_of_region_use",
        "account_takeover",
        "undocumented",
        "none",
    ]
    pattern_description: str = ""
    affected_txn_ids: list[str] = Field(default_factory=list)
    first_suspicious_txn_id: str = ""
    connected_card_ids: list[str] = Field(default_factory=list)
    connected_device_profiles: list[str] = Field(default_factory=list)
    exposure_usd: float = 0.0
    evidence: list[Evidence] = Field(default_factory=list)
    similar_prior_cases: list[str] = Field(default_factory=list)
    summary: str = ""
    written_to_graph: bool = False
    graph_case_id: str = ""


class InvestigationAnswer(BaseModel):
    case_id: str
    case: CaseRecord
    evidence_requests: list[EvidenceRequest] = Field(default_factory=list)
    next_best_actions: NextBestActions
    sar: Sar
    stop_reason: str
    tool_calls: int = 0
    tokens: int = 0
    latency_s: float = 0.0
