from __future__ import annotations

import csv

from main import _clean_evidence, _clean_prior_cases


def test_case_pack_has_20_cases():
    with open("case_pack.csv", newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))

    assert len(rows) == 20
    assert [row["case_id"] for row in rows[:3]] == ["HHG-001", "HHG-002", "HHG-003"]
    assert rows[-1]["case_id"] == "HHG-020"


def test_clean_evidence_removes_placeholder_stubs():
    evidence = [
        {
            "claim": "Live graph tool get_transaction returned evidence, but the model did not complete its structured summary",
            "source": "graph",
            "signals": ["placeholder"],
            "entity_ids": ["T1"],
            "ref": "graph",
        },
        {
            "claim": "Real suspicious activity found",
            "source": "graph",
            "signals": ["unusual_transaction"],
            "entity_ids": ["T1"],
            "ref": "graph",
        },
    ]

    cleaned = _clean_evidence(evidence)

    assert len(cleaned) == 1
    assert cleaned[0].claim == "Real suspicious activity found"


def test_clean_prior_cases_keeps_only_valid_history(tmp_path):
    history_file = tmp_path / "closed_cases_history.csv"
    history_file.write_text(
        "case_id,customer_id\nCC-100,C100\nCC-101,C101\n",
        encoding="utf-8",
    )

    payloads = [{"cases": [{"case_id": "CC-100"}, {"id": "CC-101"}, {"case_id": "fake"}, {"id": "C100"}]}]
    prior_cases = _clean_prior_cases(payloads, path=history_file)

    assert prior_cases == ["CC-100", "CC-101"]
