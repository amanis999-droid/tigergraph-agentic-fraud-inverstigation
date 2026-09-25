from __future__ import annotations

import json
from pathlib import Path
from typing import Any


TOOL_DEFINITIONS = [
    {
        "name": "get_transaction",
        "description": "Retrieve one flagged transaction and its surrounding metadata.",
        "input_schema": {
            "type": "object",
            "properties": {"txn_id": {"type": "string"}},
            "required": ["txn_id"],
        },
    },
    {
        "name": "get_device_neighbors",
        "description": "Find other cards and transactions linked to the same device profile.",
        "input_schema": {
            "type": "object",
            "properties": {"device_id": {"type": "string"}},
            "required": ["device_id"],
        },
    },
    {
        "name": "get_similar_closed_cases",
        "description": "Retrieve the most similar prior closed cases by customer, card, or pattern.",
        "input_schema": {
            "type": "object",
            "properties": {
                "customer_id": {"type": "string"},
                "card_id": {"type": "string"},
                "pattern": {"type": "string"},
            },
            "required": [],
        },
    },
]


TOOL_FUNCTIONS = {
    "get_transaction": lambda **kwargs: {"txn_id": kwargs.get("txn_id"), "transaction": {"TransactionID": kwargs.get("txn_id"), "TransactionAmt": 100.0, "channel": "online"}},
    "get_device_neighbors": lambda **kwargs: {"device_id": kwargs.get("device_id"), "neighbors": []},
    "get_similar_closed_cases": lambda **kwargs: {"cases": []},
}


def persist_case(**kwargs: Any) -> str:
    """Persist the investigation case into a graph-like output file when a real graph is unavailable."""
    case_id = str(kwargs.get("case_id") or "CASE-UNKNOWN")
    target = Path("cases") / f"{case_id}.graph.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(kwargs, indent=2), encoding="utf-8")
    return case_id
