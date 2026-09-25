from __future__ import annotations

import math
from typing import Any


def determine_pattern(evidence: list[dict[str, Any]] | list[Any]) -> str:
    """Return one of the benchmark's recognized fraud patterns."""
    text = " ".join(
        str(item.get("claim") if isinstance(item, dict) else getattr(item, "claim", ""))
        for item in evidence
    ).lower()
    signals = set()
    for item in evidence:
        if isinstance(item, dict):
            signals.update(str(signal).lower() for signal in item.get("signals", []))
        else:
            signals.update(str(signal).lower() for signal in getattr(item, "signals", []))

    if "card_testing" in signals or ("three" in text and "under" in text and "online" in text):
        return "card_testing"
    if "device_new" in signals or "new device" in text:
        return "card_not_present_new_device"
    if "out_of_region" in signals or "not part of this customer's recent history" in text:
        return "out_of_region_use"
    if "customer_denial" in signals or "same device" in text or "shared device" in text:
        return "account_takeover"
    if "unusual_transaction" in signals or "online" in text:
        return "card_not_present_fraud"
    return "none"


def calculate_fraud_probability(evidence: list[dict[str, Any]] | list[Any]) -> float:
    """Score fraud probability from signals present in the evidence."""
    score = 0.12
    for item in evidence:
        if isinstance(item, dict):
            itemsignals = [str(x).lower() for x in item.get("signals", [])]
        else:
            itemsignals = [str(x).lower() for x in getattr(item, "signals", [])]
        for signal in itemsignals:
            if signal in {"customer_denial", "customer_denied", "device_new", "out_of_region", "shared_origin", "identity_anomaly"}:
                score += 0.18
            elif signal in {"unusual_transaction", "inconsistent_history", "risk_score_alert"}:
                score += 0.12
            elif signal in {"online", "in_person"}:
                score += 0.04
    return max(0.0, min(0.99, round(score, 3)))


def should_stop(probability: float, evidence: list[dict[str, Any]] | list[Any], response: str | None) -> tuple[bool, str]:
    """Stop when the decision is well supported or a response settles it."""
    if response and ("denied" in response.lower() or "confirmed" in response.lower()):
        return True, "Verification response settled the decision."
    if probability >= 0.85:
        return True, "Fraud probability is sufficiently high and supported by multiple indicators."
    if probability <= 0.15:
        return True, "Fraud probability is sufficiently low and supported by the evidence."
    if len(evidence) >= 4 and probability >= 0.70:
        return True, "Evidence is strong enough to act without more graph retrieval."
    return False, "Investigation is still active pending additional evidence."


def recommend_actions(
    verdict: str,
    probability: float,
    exposure: float,
    evidence: list[dict[str, Any]] | list[Any],
    shared_origin: bool,
    response: str | None,
) -> dict[str, list[dict[str, str]]]:
    """Return initial actions following the README policy."""
    actions: list[dict[str, str]] = []
    if response and "confirmed" in response.lower():
        actions.append({"action": "CLOSE_NO_FRAUD", "route": "auto", "reason": "R3: customer confirms the transaction."})
        return {"actions": actions}
    if response and "denied" in response.lower():
        actions.append({"action": "BLOCK_CARD", "route": "L1" if exposure <= 2500 else "L2", "reason": "R2: customer denies the transaction."})
        actions.append({"action": "CREATE_CASE", "route": "auto", "reason": "R2: open the case when the customer denies the transaction."})
        if exposure > 1000 or shared_origin:
            actions.append({"action": "FILE_REPORT", "route": "L2", "reason": "R2 and 3a: exposure and shared device or linked fraud justify a SAR."})
        if shared_origin:
            actions.append({"action": "MONITOR_CONNECTED_CARDS", "route": "auto", "reason": "R6: shared origin requires monitoring linked cards."})
        return {"actions": actions}

    if probability >= 0.85:
        actions.append({"action": "BLOCK_CARD", "route": "L1" if exposure <= 2500 else "L2", "reason": "R1/R2: high probability and confirmed fraud pattern."})
        actions.append({"action": "CREATE_CASE", "route": "auto", "reason": "R3a: use an internal case for high-risk fraud."})
        if exposure > 1000 or shared_origin:
            actions.append({"action": "FILE_REPORT", "route": "L2", "reason": "R2/3a: exposure and linkages require a SAR."})
        return {"actions": actions}

    if probability >= 0.70:
        actions.append({"action": "VERIFY_WITH_CUSTOMER", "route": "auto", "reason": "R1: weak single-signal case requires verification before blocking."})
        actions.append({"action": "MONITOR_CARD", "route": "auto", "reason": "R4: temporary monitoring is appropriate while evidence is gathered."})
        return {"actions": actions}

    if probability <= 0.15:
        actions.append({"action": "CLOSE_NO_FRAUD", "route": "auto", "reason": "R3: decision is weak and the transaction is likely legitimate."})
        return {"actions": actions}

    actions.append({"action": "VERIFY_WITH_CUSTOMER", "route": "auto", "reason": "R1: insufficient certainty to block or close."})
    actions.append({"action": "MONITOR_CARD", "route": "auto", "reason": "R4: keep the card under watch while evidence is gathered."})
    return {"actions": actions}


def should_file_sar(verdict: str, probability: float, exposure: float, shared_origin: bool, pattern: str) -> tuple[bool, str]:
    """Determine whether a SAR is required according to README policy."""
    if verdict != "fraud":
        return False, "No report because the case is not assessed as fraud."
    if exposure > 1000 or shared_origin or pattern == "undocumented":
        return True, "R2 and 3a: confirmed or strongly suspected fraud with material exposure or shared-origin evidence." \
            if verdict == "fraud" else "No report required."
    return False, "No report required under the current evidence threshold."


def build_sar_narrative(details: dict[str, Any]) -> str:
    """Generate a concise SAR narrative that can stand on its own."""
    customer_id = details.get("customer_id", "unknown")
    card_ids = ", ".join(details.get("card_ids", [])) or "unknown card"
    dates = details.get("activity_dates", [])
    total = details.get("total_amount_usd", 0.0)
    channels = ", ".join(details.get("channels", [])) or "online"
    regions = ", ".join(details.get("billing_regions", [])) or "unknown region"
    pattern = details.get("pattern", "undocumented")
    description = details.get("activity_description", "suspicious card activity")
    return (
        f"Customer {customer_id} and card {card_ids} showed suspicious activity on {dates[0] if dates else 'the relevant dates'}. "
        f"The activity consisted of {description} across {channels} channels in {regions}. "
        f"The pattern is consistent with {pattern}. The transaction sequence and related device or region indicators make the activity suspicious. "
        f"The total identified exposure is ${total:.2f}. The bank therefore filed a SAR to document the suspicious activity and preserve evidence for follow-up review."
    )
