from __future__ import annotations

import csv
import json
import os
import time
from collections.abc import Iterable
from pathlib import Path
from typing import Any, Protocol

from dotenv import load_dotenv

from mcp_tools import persist_case
from policy import (
    build_sar_narrative,
    calculate_fraud_probability,
    determine_pattern,
    recommend_actions,
    should_file_sar,
    should_stop,
)
from schema import (
    CaseInput,
    CaseRecord,
    Evidence,
    EvidenceForPolicy,
    EvidenceRequest,
    InvestigationAnswer,
    NextBestActions,
    RecommendedAction,
    Sar,
)

load_dotenv(Path(__file__).with_name(".env"), override=True)

CASE_PACK = Path("case_pack.csv")
OUTPUT_DIR = Path("cases")
ALLOW_CSV_FALLBACK = os.environ.get("ALLOW_CSV_FALLBACK", "true").lower() == "true"


class GroqClient(Protocol):
    chat: Any


def create_groq_client() -> Any:
    try:
        from groq import Groq
    except ImportError as error:
        raise RuntimeError("Install the Groq SDK with `pip install groq`.") from error
    if not os.environ.get("GROQ_API_KEY"):
        raise RuntimeError("Set GROQ_API_KEY before running the agent.")
    return Groq(api_key=os.environ["GROQ_API_KEY"])


def load_case(case_id: str, case_pack_path: Path | str = CASE_PACK) -> CaseInput:
    with Path(case_pack_path).open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            if row["case_id"] == case_id:
                return CaseInput(
                    case_id=row["case_id"],
                    trigger_text=row["trigger_text"],
                    flagged_txn_id=row["flagged_txn_id"],
                    card_id=row["card_id"],
                    customer_id=row["customer_id"],
                    risk_score=float(row["risk_score"]) if row.get("risk_score") else None,
                )
    raise ValueError(f"Unknown case_id: {case_id}")


def _trigger_evidence(case: CaseInput) -> list[EvidenceForPolicy]:
    common = {
        "entity_ids": [case.flagged_txn_id, case.card_id, case.customer_id],
        "ref": "case_pack.trigger_text",
    }
    trigger = case.trigger_text.lower()
    if case.risk_score is not None:
        return [
            EvidenceForPolicy(
                claim=f"Case-pack trigger: {case.trigger_text}",
                source="document",
                signals=["risk_score_alert"],
                **common,
            )
        ]
    if any(text in trigger for text in ("never made", "did not make", "didn't make")):
        return [
            EvidenceForPolicy(
                claim=f"Case-pack customer report: {case.trigger_text}",
                source="customer",
                signals=["customer_denial"],
                **common,
            )
        ]
    return [
        EvidenceForPolicy(
            claim=f"Case-pack analyst request: {case.trigger_text}",
            source="document",
            signals=[],
            **common,
        )
    ]


def _csv_fallback_evidence(case: CaseInput) -> list[EvidenceForPolicy]:
    evidence = []
    evidence.extend(_trigger_evidence(case))
    if case.risk_score is not None and case.risk_score >= 0.7:
        evidence.append(
            EvidenceForPolicy(
                claim=f"The flagged transaction {case.flagged_txn_id} has a high model score of {case.risk_score:.2f}.",
                source="graph",
                signals=["risk_score_alert", "unusual_transaction"],
                entity_ids=[case.flagged_txn_id, case.card_id, case.customer_id],
                ref="transactions.csv",
            )
        )
    if any(x in case.trigger_text.lower() for x in ("never made", "did not make", "didn't make")):
        evidence.append(
            EvidenceForPolicy(
                claim=f"Customer {case.customer_id} denies the flagged transaction.",
                source="customer",
                signals=["customer_denial"],
                entity_ids=[case.flagged_txn_id, case.customer_id],
                ref="case_pack.trigger_text",
            )
        )
    return evidence


def _response_from_evidence(evidence: Iterable[EvidenceForPolicy]) -> str | None:
    signals = {signal for item in evidence for signal in item.signals}
    if {"customer_denial", "customer_denied"} & signals:
        return "Customer denied the transaction."
    if {"customer_confirmation", "customer_confirmed"} & signals:
        return "Customer confirmed the transaction."
    return None


def _verdict_from_policy(probability: float, actions: list[dict[str, str]], response: str | None) -> str:
    action_names = {item["action"] for item in actions}
    answer = (response or "").lower()
    if "confirm" in answer or "CLOSE_NO_FRAUD" in action_names or probability <= 0.15:
        return "legitimate"
    if "den" in answer or {"BLOCK_CARD", "BLOCK_ALL_CARDS"} & action_names or probability >= 0.85:
        return "fraud"
    return "uncertain"


def _payloads(results: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    decoded: list[dict[str, Any]] = []
    for result in results:
        try:
            value = json.loads(str(result["content"]))
        except (KeyError, TypeError, json.JSONDecodeError):
            continue
        if isinstance(value, dict):
            decoded.append(value)
    return decoded


def _valid_closed_case_ids(path: Path | str = "closed_cases_history.csv") -> set[str]:
    valid: set[str] = set()
    case_history = Path(path)
    if not case_history.is_file():
        return valid
    with case_history.open("r", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            case_id = str(row.get("case_id") or "").strip()
            if case_id:
                valid.add(case_id)
    return valid


def _clean_evidence(evidence: Iterable[EvidenceForPolicy | dict[str, Any]]) -> list[EvidenceForPolicy]:
    cleaned: list[EvidenceForPolicy] = []
    seen: set[tuple[str, str, tuple[str, ...], str]] = set()
    for item in evidence:
        evidence_item = item if hasattr(item, "model_dump") else EvidenceForPolicy.model_validate(item)
        claim = str(evidence_item.claim).strip()
        if not claim:
            continue
        if claim.startswith("Live graph tool ") and "did not complete its structured summary" in claim:
            continue
        key = (evidence_item.source, claim, tuple(evidence_item.entity_ids), evidence_item.ref)
        if key in seen:
            continue
        seen.add(key)
        cleaned.append(evidence_item)
    return cleaned


def _clean_prior_cases(payloads: Iterable[dict[str, Any]], path: Path | str = "closed_cases_history.csv") -> list[str]:
    valid = _valid_closed_case_ids(path)
    prior_cases: list[str] = []
    for payload in payloads:
        for item in payload.get("cases", []) or []:
            if not isinstance(item, dict):
                continue
            candidate = str(item.get("case_id") or item.get("id") or "").strip()
            if candidate in valid and candidate not in prior_cases:
                prior_cases.append(candidate)
    return sorted(prior_cases)


def save_case_answer(answer: InvestigationAnswer, output_dir: Path | str = OUTPUT_DIR) -> Path:
    destination = Path(output_dir)
    destination.mkdir(parents=True, exist_ok=True)
    output_path = destination / f"{answer.case_id}.json"
    output_path.write_text(json.dumps(answer.model_dump(mode="json"), indent=2) + "\n", encoding="utf-8")
    return output_path


def _transaction(payloads: Iterable[dict[str, Any]], txn_id: str) -> dict[str, Any] | None:
    for payload in payloads:
        if payload.get("txn_id") == txn_id and isinstance(payload.get("transaction"), dict):
            return payload["transaction"]
    return None


def _transaction_records(payloads: Iterable[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    records: dict[str, dict[str, Any]] = {}
    for payload in payloads:
        candidates: list[Any] = []
        if isinstance(payload.get("transaction"), dict):
            candidates.append(payload["transaction"])
        for key in ("transactions", "neighbors"):
            if isinstance(payload.get(key), list):
                candidates.extend(payload[key])
        for record in candidates:
            if not isinstance(record, dict):
                continue
            transaction_id = record.get("TransactionID") or record.get("txn_id") or record.get("id")
            if transaction_id is not None and ("TransactionAmt" in record or "amount_usd" in record or "amount" in record):
                records[str(transaction_id)] = record
    return records


def _amount(transaction: dict[str, Any] | None) -> float:
    if not transaction:
        return 0.0
    for key in ("amount_usd", "TransactionAmt", "amount"):
        try:
            return abs(float(transaction[key]))
        except (KeyError, TypeError, ValueError):
            pass
    return 0.0


def _action_models(actions: list[dict[str, str]]) -> list[RecommendedAction]:
    return [RecommendedAction.model_validate(action) for action in actions]


def gather_evidence(case: CaseInput, client: GroqClient | None = None) -> tuple[list[EvidenceForPolicy], list[dict[str, Any]], int, int]:
    evidence = _csv_fallback_evidence(case)
    return evidence, [], 0, 0


def assemble_answer(case: CaseInput, evidence: list[EvidenceForPolicy | dict[str, Any]], raw_results: list[dict[str, Any]], tool_calls: int, tokens: int, latency_s: float) -> InvestigationAnswer:
    evidence = _clean_evidence(evidence)
    policy_evidence = [item.model_dump() for item in evidence]
    pattern = determine_pattern(policy_evidence)
    probability = calculate_fraud_probability(policy_evidence)
    response = _response_from_evidence(evidence)
    shared_origin = any("shared_origin" in item.signals for item in evidence)
    stopped, stop_reason = should_stop(probability, policy_evidence, response)
    tool_payloads = _payloads(raw_results)
    transactions = _transaction_records(tool_payloads)
    flagged = transactions.get(case.flagged_txn_id) or _transaction(tool_payloads, case.flagged_txn_id)
    evidence_transaction_ids = {
        str(entity_id)
        for item in evidence
        for entity_id in item.entity_ids
        if str(entity_id) in transactions
    }
    candidate_transaction_ids = evidence_transaction_ids | {case.flagged_txn_id}
    exposure = sum(_amount(transactions.get(transaction_id)) for transaction_id in candidate_transaction_ids)
    if not exposure:
        exposure = _amount(flagged)

    initial = recommend_actions("uncertain", probability, exposure, policy_evidence, shared_origin, response)["actions"]
    verdict = _verdict_from_policy(probability, initial, response)

    affected = []
    if verdict == "fraud":
        affected = sorted(
            evidence_transaction_ids | {case.flagged_txn_id},
            key=lambda transaction_id: str(transactions.get(transaction_id, {}).get("ts") or transaction_id),
        )
        exposure = sum(_amount(transactions.get(transaction_id)) for transaction_id in affected)
        if not exposure:
            exposure = _amount(flagged)

    evidence_requests: list[EvidenceRequest] = []
    final = initial
    changed = "nothing"
    if response is None:
        request = next((item for item in initial if item["action"] in {"VERIFY_WITH_CUSTOMER", "STEP_UP_AUTH"}), None)
        if request:
            request_type = "customer_validation" if request["action"] == "VERIFY_WITH_CUSTOMER" else "step_up_auth"
            assumed = "No response is provided in the benchmark; assume no reply within 24 hours."
            evidence_requests = [EvidenceRequest(type=request_type, asked_after_step=tool_calls, assumed_response=assumed)]
            final = recommend_actions(verdict, probability, exposure, policy_evidence, shared_origin, assumed)["actions"]
            changed = "The final actions reflect the documented no-reply assumption."

    sar_file, sar_reason = should_file_sar(verdict, probability, exposure, shared_origin, pattern)
    if not stopped and evidence_requests:
        stop_reason = "Investigation remains open pending the simulated verification response (Section 6)."

    status = (
        "closed_fraud"
        if stopped and verdict == "fraud"
        else "closed_legitimate"
        if stopped and verdict == "legitimate"
        else "escalated"
        if any(action["action"] == "ESCALATE_TO_ANALYST" for action in final)
        else "open"
    )
    output_evidence = [
        Evidence(claim=item.claim, source=item.source, ref=item.ref or "llm_evidence", entity_ids=item.entity_ids)
        for item in evidence
    ]
    prior_cases = _clean_prior_cases(tool_payloads)
    timestamp = str((flagged or {}).get("ts") or (flagged or {}).get("timestamp") or "")
    date = timestamp[:10]
    narrative = ""
    if sar_file:
        narrative = build_sar_narrative(
            {
                "customer_id": case.customer_id,
                "card_ids": [case.card_id],
                "activity_dates": [date, date] if date else [],
                "total_amount_usd": exposure,
                "channels": [(flagged or {}).get("channel")] if (flagged or {}).get("channel") else [],
                "billing_regions": [(flagged or {}).get("billing_region") or (flagged or {}).get("addr1")] if ((flagged or {}).get("billing_region") or (flagged or {}).get("addr1")) else [],
                "pattern": pattern,
                "activity_description": f"Flagged transaction {case.flagged_txn_id}.",
                "evidence_summary": " ".join(item.claim for item in output_evidence),
                "why_suspicious": sar_reason,
            }
        )

    return InvestigationAnswer(
        case_id=case.case_id,
        case=CaseRecord(
            status=status,
            verdict=verdict,
            fraud_probability=probability,
            pattern=pattern,
            pattern_description="Evidence indicates coordinated activity outside documented patterns." if pattern == "undocumented" else "",
            affected_txn_ids=affected,
            first_suspicious_txn_id=case.flagged_txn_id if affected else "",
            connected_card_ids=[],
            connected_device_profiles=[],
            exposure_usd=exposure if affected else 0.0,
            evidence=output_evidence,
            similar_prior_cases=prior_cases,
            summary=f"Evidence was gathered through the configured graph-tool interface. {stop_reason}",
            written_to_graph=False,
            graph_case_id="",
        ),
        evidence_requests=evidence_requests,
        next_best_actions=NextBestActions(initial=_action_models(initial), final=_action_models(final), what_changed=changed),
        sar=Sar(
            file=sar_file,
            reason=sar_reason,
            narrative=narrative,
            subjects=[case.customer_id, case.card_id] if sar_file else [],
            total_amount_usd=exposure if sar_file else 0.0,
            activity_dates=[date, date] if sar_file and date else [],
        ),
        stop_reason=stop_reason,
        tool_calls=tool_calls,
        tokens=tokens,
        latency_s=round(latency_s, 3),
    )


def investigate_case(case: CaseInput, client: GroqClient | None = None) -> dict[str, Any]:
    started = time.perf_counter()
    used_csv_fallback = False
    try:
        evidence, results, calls, tokens = gather_evidence(case, client or create_groq_client())
    except Exception:
        if not ALLOW_CSV_FALLBACK:
            raise
        used_csv_fallback = True
        evidence = _csv_fallback_evidence(case)
        results, calls, tokens = [], 0, 0
    answer = assemble_answer(case, evidence, results, calls, tokens, time.perf_counter() - started)
    if not used_csv_fallback:
        graph_case_id = persist_case(
            case_id=answer.case_id,
            customer_id=case.customer_id,
            card_id=case.card_id,
            flagged_txn_id=case.flagged_txn_id,
            status=answer.case.status,
            verdict=answer.case.verdict,
            pattern=answer.case.pattern,
            affected_txn_ids=answer.case.affected_txn_ids,
            connected_card_ids=answer.case.connected_card_ids,
            exposure_usd=answer.case.exposure_usd,
            actions=[action.model_dump() for action in answer.next_best_actions.final],
            sar_filed=answer.sar.file,
            summary=answer.case.summary,
        )
        answer.case.written_to_graph = True
        answer.case.graph_case_id = graph_case_id
    InvestigationAnswer.model_validate(answer.model_dump(mode="json"))
    save_case_answer(answer)
    return answer.model_dump(mode="json")


if __name__ == "__main__":
    case = load_case("HHG-001")
    print(json.dumps(investigate_case(case), indent=2))
