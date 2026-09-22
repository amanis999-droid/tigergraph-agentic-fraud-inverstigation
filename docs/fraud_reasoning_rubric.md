# Fraud-investigation reasoning rubric

This rubric is the human-readable counterpart to `policy.py`. It implements the
Fraud Policy in `README.md`; it does not turn a model risk score into a verdict.
The graph/orchestration layer gathers evidence, while the policy layer classifies
that evidence and returns the exact action names, approval routes, and JSON field
values required by the answer format.

## Evidence contract and audit trail

Every evidence item passed to the policy module has at least these answer-format
fields: `claim`, `source`, and `entity_ids`. `source` remains one of `graph`,
`document`, `customer`, or `external` when the item is written to the final case.
For reliable automation, the orchestration layer may also attach normalized
`signals`, such as `card_testing`, `new_device`, `closed_confirmed_fraud_link`,
`shared_origin`, `customer_denial`, or `customer_confirmation`. The module can
also recognize conservative phrases in `claim`, but explicit signals are easier
to audit.

The agent should preserve the graph query or document section in the answer
format's `evidence[].ref`. It should cite closed-case IDs in
`similar_prior_cases`; a closed case is evidence, not a substitute for checking
the current activity.

## Probability calibration

`calculate_fraud_probability(evidence)` is explainable rather than model-like.
It starts at **0.30** and adds the corroboration below. The final value is capped
at 0.98 and rounded to two decimal places.

| Evidence state | Policy score treatment | Expected band |
|---|---|---:|
| Bare risk-score alert or one unusual transaction | Base 0.30 plus up to 0.20 for alert/unusual-history evidence; no uncorroborated case can exceed 0.50 | 0.30–0.50 |
| Recognizable graph pattern | Add 0.25 for a named or undocumented pattern; a new-device CNP pattern adds a further 0.05 | 0.50–0.70 |
| Pattern plus a closed `confirmed_fraud` link | Add 0.18 for a device, region, recipient, or ring link to labeled history | 0.70–0.85 |
| Pattern plus a shared origin across cards | Add 0.30 for a shared device, region, recipient, ring, or multiple-card evidence | 0.85+ |
| Customer denial | Add 0.30; combined with a pattern this ordinarily reaches 0.85+ | 0.85+ |
| Customer confirms the transaction | Override the result to 0.10 | <=0.15 |

This supports **R1** (verify weak evidence below 0.70), **R2** (customer denial
materially changes the assessment), **R5** (the testing sequence is strong
evidence), and **R8** (uncertain, exposed cases escalate). It is an assessment
of the complete evidence set, never a copy of `risk_score`.

## Pattern classification

`determine_pattern(evidence)` returns exactly one of the answer-format values:
`card_testing`, `card_not_present_fraud`, `card_not_present_new_device`,
`out_of_region_use`, `account_takeover`, `undocumented`, or `none`.

| Returned value | Required facts | README policy basis |
|---|---|---|
| `card_testing` | Three or more tiny online authorizations on one card within an hour, then a larger purchase | Known pattern 1; **R5** |
| `card_not_present_fraud` | Online activity inconsistent with that cardholder's history, normally a short burst rather than one merely unusual purchase | Known pattern 2 |
| `card_not_present_new_device` | Card-not-present evidence plus a device marked `New` for the account; proxy evidence can strengthen it | Known pattern 3 |
| `out_of_region_use` | Card-present use in a new billing region while normal home activity continues; do not call a multi-day trip a clone without more evidence | Known pattern 4; **R2–R3** |
| `account_takeover` | Mixed-channel inconsistency together with device, match-flag, or credential anomalies | Known pattern 5; **R10** may matter if credentials are confirmed compromised |
| `undocumented` | Coordinated or repeated abuse across customers/cards that genuinely fits none of the five named patterns | **R9** |
| `none` | The supplied evidence does not support a pattern | **R1** and **R8** determine the safe next step |

Explicit normalized signals take priority. In particular, the more specific
`card_not_present_new_device` wins over generic card-not-present fraud. The
agent must not force unusual activity into a named pattern simply to obtain a
more decisive action.

## When to stop

`should_stop(probability, evidence, verification_response)` stops only when a
Fraud Policy Section 6 condition is met:

1. Fraud probability is at least 0.85 and there are two or more independent
   evidence items.
2. Fraud probability is at most 0.15 and there are two or more independent
   evidence items.
3. A customer/verification response expressly denies or confirms the activity.
4. The evidence expressly records that further steps are unlikely to change the
   decision.

Independent items are distinct `source`/`claim` pairs. Repeating the same graph
finding twice does not create independent corroboration. If none of these
conditions hold, keep the case open or escalate/request evidence as the rules
below require, and write the returned explanation to `stop_reason`.

## Action decision table

The `next_best_actions.initial` and `next_best_actions.final` arrays use objects
with exactly `action`, `route`, and `reason`. Action identifiers and routes are
not renamed. `auto` actions may be executed by the agent; `L1` and `L2` actions
are recommendations awaiting human approval.

| Rule | Decision | Exact action(s) and route |
|---|---|---|
| **R1** | Single weak signal and probability below 0.70 | `VERIFY_WITH_CUSTOMER` / `auto` before a block. For a testing sequence, this still applies to any block not independently supported by R5. |
| **R2** | Customer denies the transaction | `BLOCK_CARD` / `L1` if exposure is <= $2,500, otherwise `L2`; `CREATE_CASE` / `auto`. Add `FILE_REPORT` / `L2` when exposure exceeds $1,000 or there is a shared origin/related card. |
| **R3** | Customer confirms the transaction | `CLOSE_NO_FRAUD` / `auto`. |
| **R4** | No reply within 24 hours | `MONITOR_CARD` / `auto` and `DECLINE_TRANSACTION` / `L1` for pending authorizations. Add `ESCALATE_TO_ANALYST` / `auto` when exposure exceeds $500. |
| **R5** | Three-plus small online authorizations followed by a larger purchase | `DECLINE_TRANSACTION` / `L1` and `STEP_UP_AUTH` / `auto`. If a purchase above $100 cleared, add `BLOCK_CARD` / `L1` when exposure is <= $2,500, otherwise `L2`. |
| **R6** | Several cards share a fraud origin (device, region, recipient, or ring) | `CREATE_CASE` / `auto`, `FILE_REPORT` / `L2`, and `MONITOR_CONNECTED_CARDS` / `auto` after fraud is confirmed or strongly suspected. Name the shared element in evidence. |
| **R7** | Customer disputes a charge matching their own recurring merchant/amount/cadence | `CREATE_CASE` / `auto`, `VERIFY_WITH_CUSTOMER` / `auto`, and `WARN_CUSTOMER` / `auto`. Do not block. |
| **R8** | Verdict is `uncertain` and exposure exceeds $500, or evidence conflicts | `ESCALATE_TO_ANALYST` / `auto`. |
| **R9** | Coordinated abuse fits no named pattern | `CREATE_CASE` / `auto`, `FILE_REPORT` / `L2`, and `ESCALATE_TO_ANALYST` / `auto`; return `undocumented` and explain it in `pattern_description`. |
| **R10** | At least two cards have confirmed fraud, or credentials are confirmed compromised | `BLOCK_ALL_CARDS` / `L2` is permitted. It must never be recommended otherwise. |

There are several general safeguards:

- Under Section 3a, create an internal case whenever probability reaches 0.30,
  the agent requests evidence, or a customer disputes a charge.
- `BLOCK_CARD` is `L1` through $2,500 exposure and `L2` above that amount.
- `DECLINE_TRANSACTION` is always `L1`; `FILE_REPORT` and
  `BLOCK_ALL_CARDS` are always `L2`.
- `ALLOW_TRANSACTION`, `MONITOR_CARD`, `MONITOR_CONNECTED_CARDS`,
  `WARN_CUSTOMER`, `VERIFY_WITH_CUSTOMER`, `STEP_UP_AUTH`,
  `GENERATE_REPORT`, `CREATE_CASE`, `ESCALATE_TO_ANALYST`, and
  `CLOSE_NO_FRAUD` use `auto`.

## SAR decision and narrative

`should_file_sar(verdict, probability, exposure_usd, shared_device_or_region,
pattern)` implements **R6**, **R9**, and Policy Section **3a**. A SAR is filed
only if fraud is confirmed (`verdict == "fraud"`) or strongly suspected
(probability >= 0.85), and at least one of these applies:

- exposure is greater than $1,000;
- it connects to a shared device, region, or related card/ring (**R6**); or
- the activity is coordinated or `undocumented` (**R9**).

Otherwise the agent can still create a case; a case and a SAR are different
deliverables. `sar.file` must agree with the presence of `FILE_REPORT` in the
final action list. When false, the answer format requires `sar.narrative` to be
`""`, `sar.subjects` to be `[]`, `sar.total_amount_usd` to be `0`, and
`sar.activity_dates` to be `[]`.

`build_sar_narrative(case_data)` writes nine factual sentences, satisfying the
required six-to-twelve sentence range. It only names fields supplied by the
caller and deliberately says `not supplied` when a required fact is absent
rather than inventing details. Supply these fields to make the narrative useful:

```text
customer_id, card_ids, activity_dates, total_amount_usd,
channels, billing_regions, connected_device_profiles, pattern,
activity_description, evidence_summary, why_suspicious
```

The narrative sequence is: who (customer/cards), what (activity), when (dates),
where (channel/region), amount, pattern/how, device/ring connection, evidence,
and why suspicious. The final answer places it in `sar.narrative`, with actual
subject IDs in `sar.subjects`, the episode total in `sar.total_amount_usd`, and
the first/last dates in `sar.activity_dates`.

## Answer-format handoff checklist

The policy module does not create files or graph vertices. The orchestration
layer maps its outputs into the exact top-level answer schema:

```text
case_id, case, evidence_requests, next_best_actions, sar,
stop_reason, tool_calls, tokens, latency_s
```

For `case`, retain the exact fields `status`, `verdict`, `fraud_probability`,
`pattern`, `pattern_description`, `affected_txn_ids`,
`first_suspicious_txn_id`, `connected_card_ids`,
`connected_device_profiles`, `exposure_usd`, `evidence`,
`similar_prior_cases`, `summary`, `written_to_graph`, and `graph_case_id`.
For `next_best_actions`, write the policy output into `initial` and `final`,
then explain evidence-driven changes in `what_changed`. A legitimate case has
empty `affected_txn_ids`, `exposure_usd` of 0, and no SAR.
