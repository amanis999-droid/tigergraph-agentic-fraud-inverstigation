"""Pure, explainable policy logic for the Fraud Investigation Dataset.

The orchestration layer supplies graph/document/customer evidence as dictionaries.
This module never queries data or writes cases; it only turns supplied evidence into
consistent policy recommendations.
"""

from __future__ import annotations

from typing import Any


Evidence = dict[str, Any]
Action = dict[str, str]

_PATTERNS = {
    "card_testing",
    "card_not_present_fraud",
    "card_not_present_new_device",
    "out_of_region_use",
    "account_takeover",
    "undocumented",
    "none",
}


def _normalise(value: object) -> str:
    """Normalise a supplied signal or text fragment for matching."""
    return str(value).lower().replace("-", "_").replace(" ", "_")


def _signals(evidence: list[Evidence]) -> set[str]:
    """Collect optional, orchestration-supplied normalized signals from evidence."""
    found: set[str] = set()
    for item in evidence:
        raw = item.get("signals", [])
        if isinstance(raw, str):
            raw = [raw]
        if isinstance(raw, (list, tuple, set)):
            found.update(_normalise(signal) for signal in raw)
        for key, value in item.items():
            if value is True:
                found.add(_normalise(key))
    return found


def _text(evidence: list[Evidence]) -> str:
    """Return evidence claims as a lower-case searchable string."""
    return " ".join(str(item.get("claim", "")).lower() for item in evidence)


def _has(evidence: list[Evidence], signal: str, *phrases: str) -> bool:
    """Match either an explicit signal or a conservative phrase in an evidence claim."""
    normalized = _normalise(signal)
    if normalized in _signals(evidence):
        return True
    claim_text = _text(evidence)
    return any(phrase.lower() in claim_text for phrase in phrases)


def _max_numeric(evidence: list[Evidence], key: str) -> float | None:
    """Read an optional numeric fact supplied on one or more evidence items."""
    values: list[float] = []
    for item in evidence:
        value = item.get(key)
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            values.append(float(value))
    return max(values) if values else None


def _response_kind(response: str | None) -> str:
    """Classify an explicit customer/verification response without guessing intent."""
    if not response:
        return "none"
    value = response.lower()
    if any(word in value for word in ("did not", "didn't", "deny", "unauthorized", "not mine", "never made")):
        return "denied"
    if any(word in value for word in ("confirmed", "authorised", "authorized", "i made", "my purchase")):
        return "confirmed"
    if any(word in value for word in ("no reply", "no response", "unreachable")):
        return "no_reply"
    return "none"


def _evidence_response(evidence: list[Evidence]) -> str:
    """Find an explicit customer outcome recorded as a normalized evidence signal."""
    signals = _signals(evidence)
    if {"customer_confirmation", "customer_confirmed"} & signals:
        return "confirmed"
    if {"customer_denial", "customer_denied"} & signals:
        return "denied"
    if {"no_reply", "customer_no_reply"} & signals:
        return "no_reply"
    return "none"


def _independent_evidence_count(evidence: list[Evidence]) -> int:
    """Count distinct claim/source pairs for the Section 6 two-evidence check."""
    distinct = {
        (str(item.get("source", "unknown")).lower(), str(item.get("claim", "")).strip().lower())
        for item in evidence
        if str(item.get("claim", "")).strip()
    }
    return len(distinct)


def _append(actions: list[Action], action: str, route: str, reason: str) -> None:
    """Append an action once, retaining the first (highest-priority) policy reason."""
    if not any(existing["action"] == action for existing in actions):
        actions.append({"action": action, "route": route, "reason": reason})


def _has_card_testing_sequence(evidence: list[Evidence]) -> bool:
    """Identify R5's three-small-online-authorizations then larger-purchase sequence."""
    count = _max_numeric(evidence, "small_online_authorization_count")
    explicit = _has(evidence, "card_testing", "card testing")
    sequence_words = (
        "three small online authorizations",
        "three online authorizations",
        "three tiny online",
        "sub-$",
    )
    larger_purchase = _has(evidence, "larger_purchase_after_testing", "larger purchase", "followed by a larger")
    return explicit or ((count is not None and count >= 3 and larger_purchase) or (any(word in _text(evidence) for word in sequence_words) and larger_purchase))


def calculate_fraud_probability(evidence: list[Evidence]) -> float:
    """Implement the README calibration guidance used with R1, R2, R5, and R8.

    The score is intentionally additive: a weak alert starts at 0.30; an unusual
    transaction/risk alert adds up to 0.20; a recognizable pattern adds 0.25; a
    closed confirmed-fraud link adds 0.18; and a shared origin or customer denial
    adds 0.30. Customer confirmation overrides all other signals to 0.10.
    """
    response = _evidence_response(evidence)
    if response == "confirmed":
        return 0.10

    score = 0.30
    weak_signal = _has(evidence, "risk_score_alert", "risk score", "model scored") or _has(
        evidence, "unusual_transaction", "unusual transaction", "does not fit", "never used"
    )
    if weak_signal:
        score += 0.10
    if _has(evidence, "unusual_transaction", "unusual transaction", "does not fit", "never used"):
        score += 0.08

    pattern = determine_pattern(evidence)
    if pattern != "none":
        score += 0.25
    if pattern == "card_not_present_new_device":
        score += 0.05
    if _has(evidence, "closed_confirmed_fraud_link", "closed confirmed fraud", "confirmed_fraud case"):
        score += 0.18
    if _has(evidence, "shared_origin", "shared device", "shared region", "shared recipient") or _has(
        evidence, "multiple_cards", "multiple cards", "other cards"
    ):
        score += 0.30
    if response == "denied":
        score += 0.30

    # A bare alert or one unusual purchase stays in the stipulated 0.30--0.50 band.
    if pattern == "none" and response == "none" and not _has(
        evidence, "closed_confirmed_fraud_link", "closed confirmed fraud", "confirmed_fraud case"
    ):
        score = min(score, 0.50)
    return round(min(max(score, 0.0), 0.98), 2)


def determine_pattern(evidence: list[Evidence]) -> str:
    """Classify the five README patterns or R9's ``undocumented`` pattern.

    Evidence may provide explicit ``signals`` (recommended) or describe the facts in
    ``claim``. The function does not infer a named pattern from a risk score alone.
    """
    explicit = _signals(evidence) & _PATTERNS
    if explicit:
        # More specific new-device CNP takes precedence over generic CNP.
        return "card_not_present_new_device" if "card_not_present_new_device" in explicit else sorted(explicit)[0]

    online = _has(evidence, "online", " online", "channel online")
    new_device = _has(evidence, "new_device", "device marked new", "new for this account")
    if _has_card_testing_sequence(evidence):
        return "card_testing"
    if online and new_device and _has(evidence, "inconsistent_history", "does not fit", "never used", "unusual"):
        return "card_not_present_new_device"
    if online and _has(evidence, "inconsistent_history", "does not fit", "never used", "unusual"):
        return "card_not_present_fraud"
    if _has(evidence, "out_of_region", "new billing region", "out-of-region") and _has(
        evidence, "in_person", "in person", "card-present"
    ):
        return "out_of_region_use"
    if _has(evidence, "account_takeover", "mixed-channel", "mixed channel") and _has(
        evidence, "credential_anomaly", "match-flag anomaly", "device anomaly"
    ):
        return "account_takeover"
    if _has(evidence, "coordinated_abuse", "coordinated", "repeated abuse") and _has(
        evidence, "multiple_customers", "across customers", "multiple cards"
    ):
        return "undocumented"
    return "none"


def should_stop(
    probability: float, evidence: list[Evidence], verification_response: str | None
) -> tuple[bool, str]:
    """Implement Fraud Policy Section 6 stopping conditions.

    Stop for a settled customer response; for an extreme probability supported by at
    least two distinct claim/source pairs; or when evidence explicitly records that
    further work cannot change the decision.
    """
    response = _response_kind(verification_response)
    if response == "none":
        response = _evidence_response(evidence)
    if response in {"denied", "confirmed"}:
        return True, "Verification response settled the question (Section 6)."
    if _has(evidence, "decision_final", "further steps are unlikely", "will not change the decision"):
        return True, "Further steps are unlikely to change the decision (Section 6)."
    if probability >= 0.85 and _independent_evidence_count(evidence) >= 2:
        return True, "Fraud probability is at least 0.85 with two or more independent evidence items (Section 6)."
    if probability <= 0.15 and _independent_evidence_count(evidence) >= 2:
        return True, "Fraud probability is at most 0.15 with two or more independent evidence items (Section 6)."
    return False, "More evidence could still change the decision (Section 6)."


def should_file_sar(
    verdict: str,
    probability: float,
    exposure_usd: float,
    shared_device_or_region: bool,
    pattern: str,
) -> tuple[bool, str]:
    """Implement R6, R9, and Fraud Policy Section 3a SAR-filing thresholds."""
    confirmed_or_strong = verdict == "fraud" or probability >= 0.85
    if not confirmed_or_strong:
        return False, "Section 3a: fraud is not confirmed or strongly suspected."
    if pattern == "undocumented":
        return True, "R9 and Section 3a: coordinated or undocumented suspicious activity requires a report."
    if shared_device_or_region:
        return True, "R6 and Section 3a: suspected fraud connects through a shared device, region, or related card."
    if exposure_usd > 1000:
        return True, "Section 3a: confirmed or strongly suspected fraud exposure exceeds $1,000."
    return False, "Section 3a: no report threshold or shared/undocumented-pattern condition is met."


def recommend_actions(
    verdict: str,
    probability: float,
    exposure_usd: float,
    evidence: list[Evidence],
    shared_device_or_region: bool,
    customer_response: str | None,
) -> dict[str, list[Action]]:
    """Apply Fraud Policy R1--R10 and return exact policy action/route identifiers.

    ``customer_response`` takes precedence over any response signal in evidence. The
    returned list is ordered by the action that should happen first.
    """
    actions: list[Action] = []
    response = _response_kind(customer_response)
    if response == "none":
        response = _evidence_response(evidence)
    pattern = determine_pattern(evidence)
    disputed_recurring = _has(evidence, "recurring_pattern", "same merchant", "recurring pattern") and _has(
        evidence, "customer_dispute", "customer disputes", "disputed charge"
    )
    credentials_compromised = _has(evidence, "credentials_confirmed_compromised", "credentials confirmed compromised")
    two_confirmed_cards = _has(evidence, "two_confirmed_cards", "two cards show confirmed fraud")

    # R3 settles a customer-confirmed alert before other alert mechanics are applied.
    if response == "confirmed":
        _append(actions, "CLOSE_NO_FRAUD", "auto", "R3: customer confirmed the transaction.")
        return {"actions": actions}

    # R7 is intentionally checked before generic R1 verification handling.
    if disputed_recurring:
        _append(actions, "CREATE_CASE", "auto", "R7: disputed charge matches the customer's recurring pattern.")
        _append(actions, "VERIFY_WITH_CUSTOMER", "auto", "R7: confirm the recurring charge with the customer.")
        _append(actions, "WARN_CUSTOMER", "auto", "R7: provide a recurring-charge reminder; do not block.")
        return {"actions": actions}

    if response == "denied":
        if two_confirmed_cards or credentials_compromised:
            _append(actions, "BLOCK_ALL_CARDS", "L2", "R10: two cards have confirmed fraud or credentials are confirmed compromised.")
        else:
            route = "L2" if exposure_usd > 2500 else "L1"
            _append(actions, "BLOCK_CARD", route, "R2: customer denied the transaction; block and reissue the affected card.")
        _append(actions, "CREATE_CASE", "auto", "R2: customer denial requires an internal fraud case.")
        file_sar, sar_reason = should_file_sar("fraud", probability, exposure_usd, shared_device_or_region, pattern)
        if file_sar:
            _append(actions, "FILE_REPORT", "L2", sar_reason)
        if shared_device_or_region:
            _append(actions, "MONITOR_CONNECTED_CARDS", "auto", "R6: monitor cards sharing the identified origin.")
        return {"actions": actions}

    if response == "no_reply":
        _append(actions, "MONITOR_CARD", "auto", "R4: no customer reply within 24 hours.")
        if _has(evidence, "pending_authorization", "pending authorization", "pending authorizations"):
            _append(actions, "DECLINE_TRANSACTION", "L1", "R4: decline pending authorizations after no reply.")
        if exposure_usd > 500:
            _append(actions, "ESCALATE_TO_ANALYST", "auto", "R4: exposure exceeds $500 after no reply.")

    if pattern == "card_testing":
        _append(actions, "DECLINE_TRANSACTION", "L1", "R5: card-testing sequence requires declining the flagged authorization.")
        _append(actions, "STEP_UP_AUTH", "auto", "R5: card-testing sequence requires step-up authentication.")
        cleared_amount = _max_numeric(evidence, "cleared_purchase_amount") or 0.0
        if cleared_amount > 100:
            route = "L2" if exposure_usd > 2500 else "L1"
            _append(actions, "BLOCK_CARD", route, "R5: a purchase over $100 has already cleared.")

    if probability < 0.70 and response == "none" and pattern != "card_testing":
        _append(actions, "VERIFY_WITH_CUSTOMER", "auto", "R1: single weak signal, probability below 0.70; verify before blocking.")
    elif probability < 0.70 and response == "none" and pattern == "card_testing":
        _append(actions, "VERIFY_WITH_CUSTOMER", "auto", "R1: obtain confirmation before any block not already supported by R5.")

    if probability >= 0.30 or response != "none":
        _append(actions, "CREATE_CASE", "auto", "Section 3a: probability reaches 0.30 or evidence was requested, so open a case.")

    if shared_device_or_region and (verdict == "fraud" or probability >= 0.70):
        _append(actions, "MONITOR_CONNECTED_CARDS", "auto", "R6: monitor all cards sharing the device, region cluster, or ring.")

    if pattern == "undocumented":
        _append(actions, "CREATE_CASE", "auto", "R9: coordinated undocumented activity requires an internal case.")
        _append(actions, "ESCALATE_TO_ANALYST", "auto", "R9: describe and escalate the undocumented coordinated pattern.")

    file_sar, sar_reason = should_file_sar(verdict, probability, exposure_usd, shared_device_or_region, pattern)
    if file_sar:
        _append(actions, "FILE_REPORT", "L2", sar_reason)

    conflicting = _has(evidence, "evidence_conflict", "evidence conflicts", "conflicting evidence")
    if verdict == "uncertain" and (exposure_usd > 500 or conflicting):
        _append(actions, "ESCALATE_TO_ANALYST", "auto", "R8: uncertain verdict with exposure over $500 or conflicting evidence.")

    if verdict == "legitimate" and probability <= 0.15:
        _append(actions, "CLOSE_NO_FRAUD", "auto", "R3/Section 6: evidence supports a legitimate conclusion.")
    return {"actions": actions}


def build_sar_narrative(case_data: dict[str, Any]) -> str:
    """Build a factual 6--12 sentence SAR narrative required by Policy Section 3a.

    Only values present in ``case_data`` are named. Useful optional fields are
    ``customer_id``, ``card_ids``, ``activity_dates``, ``total_amount_usd``,
    ``channels``, ``billing_regions``, ``connected_device_profiles``,
    ``pattern``, ``activity_description``, ``evidence_summary``, and
    ``why_suspicious``.
    """
    def listed(value: Any, fallback: str) -> str:
        if isinstance(value, (list, tuple, set)):
            return ", ".join(str(item) for item in value) if value else fallback
        return str(value) if value not in (None, "") else fallback

    customer = listed(case_data.get("customer_id", case_data.get("customer")), "not supplied")
    cards = listed(case_data.get("card_ids", case_data.get("connected_card_ids")), "not supplied")
    dates = listed(case_data.get("activity_dates"), "not supplied")
    amount = case_data.get("total_amount_usd", case_data.get("exposure_usd"))
    amount_text = f"${float(amount):,.2f}" if isinstance(amount, (int, float)) and not isinstance(amount, bool) else "not supplied"
    channels = listed(case_data.get("channels", case_data.get("channel")), "not supplied")
    regions = listed(case_data.get("billing_regions", case_data.get("billing_region")), "not supplied")
    devices = listed(case_data.get("connected_device_profiles"), "not supplied")
    pattern = listed(case_data.get("pattern"), "not supplied")
    activity = listed(case_data.get("activity_description"), "activity details were not supplied")
    evidence_summary = listed(case_data.get("evidence_summary", case_data.get("summary")), "an evidence summary was not supplied")
    why = listed(case_data.get("why_suspicious"), "the supplied evidence indicates activity inconsistent with the recorded case context")

    sentences = [
        f"This report concerns customer {customer} and card or cards {cards}.",
        f"The bank identified the following activity: {activity}.",
        f"The activity dates recorded in the case are {dates}.",
        f"The recorded channel or channels are {channels}, and the recorded billing region or regions are {regions}.",
        f"The total suspicious amount recorded in the case is {amount_text}.",
        f"The case assesses the pattern as {pattern}.",
        f"Recorded device profile or profiles are {devices}.",
        f"Supporting evidence is summarized as follows: {evidence_summary}.",
        f"The activity is suspicious because {why}.",
    ]
    return " ".join(sentences)


if __name__ == "__main__":
    example_evidence: list[Evidence] = [
        {
            "claim": "Three small online authorizations were followed by a larger purchase.",
            "source": "graph",
            "entity_ids": ["TXN-1", "TXN-2"],
            "signals": ["card_testing", "larger_purchase_after_testing"],
            "small_online_authorization_count": 3,
            "cleared_purchase_amount": 125.00,
        },
        {
            "claim": "The customer denied the purchases.",
            "source": "customer",
            "entity_ids": [],
            "signals": ["customer_denial"],
        },
    ]
    probability = calculate_fraud_probability(example_evidence)
    print(determine_pattern(example_evidence), probability)
    print(recommend_actions("fraud", probability, 125.00, example_evidence, False, "Customer denied the purchase"))


    print("--- HHG-014 test ---")
    hhg014_evidence: list[Evidence] = [
        {
            "claim": "Several cards this month show purchases from the same unusual device profile.",
            "source": "graph",
            "entity_ids": ["C13487-K1"],
            "signals": ["shared_origin"],
        },
        # add more evidence items here once you have real graph query results
    ]
    probability = calculate_fraud_probability(hhg014_evidence)
    pattern = determine_pattern(hhg014_evidence)
    print(pattern, probability)
    print(recommend_actions("uncertain", probability, 0.0, hhg014_evidence, True, None))
