"""
FastAPI backend for the TigerGraph Agentic Fraud Investigation dashboard.

Member 3's module. Does NOT talk to TigerGraph or the AI agent directly.
Reads case JSON files matching the fixed contract and serves them to the
Next.js frontend.

WHEN THE REAL AGENT IS READY:
Replace the body of `get_case_data()` / `list_all_cases()` with a call into
the agent module or a read from wherever Member 2's agent writes output.
Replace `get_case_graph()` with a real TigerGraph MCP query (Member 1).
Nothing in the frontend needs to change if the JSON contract stays fixed.

RUN LOCALLY:
    cd backend
    pip install -r requirements.txt
    uvicorn main:app --reload --port 8000
"""

import json
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

MOCK_DATA_DIR = Path(__file__).parent.parent / "mock_data"

app = FastAPI(title="Fraud Investigation Dashboard API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

_approval_status: dict[str, str] = {}


def _load_case_file(case_id: str) -> dict:
    path = MOCK_DATA_DIR / f"{case_id}.json"
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"Case {case_id} not found")
    with open(path, "r") as f:
        return json.load(f)


def list_all_cases() -> list[dict]:
    """SWAP POINT: query the agent's case store / TigerGraph once live."""
    summaries = []
    for path in sorted(MOCK_DATA_DIR.glob("*.json")):
        with open(path, "r") as f:
            data = json.load(f)
        case = data["case"]
        summaries.append({
            "case_id": case["case_id"],
            "trigger_type": case["trigger_type"],
            "verdict": case["verdict"],
            "risk_level": case["risk_level"],
            "fraud_pattern": case["fraud_pattern"],
            "exposure_amount": case["exposure_amount"],
            "approval_status": _approval_status.get(case["case_id"], "pending"),
        })
    return summaries


def get_case_data(case_id: str) -> dict:
    """SWAP POINT: return agent.investigate(case_id) once the agent is live."""
    data = _load_case_file(case_id)
    data["case"]["approval_status"] = _approval_status.get(case_id, "pending")
    return data


def get_case_graph(case_id: str) -> dict:
    """
    Returns a node/edge graph for the Graph UI panel.
    SWAP POINT: replace with a real TigerGraph MCP query from Member 1.
    """
    data = _load_case_file(case_id)
    case = data["case"]

    nodes = [
        {"id": case["customer_id"], "label": case["customer_id"], "type": "customer"},
        {"id": case["card_id"], "label": case["card_id"], "type": "card"},
        {"id": case["flagged_transaction_id"], "label": case["flagged_transaction_id"], "type": "transaction"},
    ]
    edges = [
        {"source": case["customer_id"], "target": case["card_id"], "label": "owns"},
        {"source": case["card_id"], "target": case["flagged_transaction_id"], "label": "used_in"},
    ]

    if any(e["source"] == "device" for e in case["evidence"]):
        device_id = f"DEV-{case['card_id'][-4:]}"
        nodes.append({"id": device_id, "label": device_id, "type": "device"})
        edges.append({"source": case["flagged_transaction_id"], "target": device_id, "label": "seen_on"})

    for prior in case["similar_past_cases"]:
        nodes.append({"id": prior, "label": prior, "type": "prior_case"})
        edges.append({"source": case["card_id"], "target": prior, "label": "similar_to"})

    return {"case_id": case_id, "nodes": nodes, "edges": edges}


class ApprovalRequest(BaseModel):
    approved: bool
    approver: Optional[str] = "analyst_demo"


@app.get("/cases")
def get_cases():
    return list_all_cases()


@app.get("/cases/{case_id}")
def get_case(case_id: str):
    return get_case_data(case_id)


@app.get("/cases/{case_id}/graph")
def get_graph(case_id: str):
    return get_case_graph(case_id)


@app.post("/cases/{case_id}/approve")
def approve_case(case_id: str, body: ApprovalRequest):
    _load_case_file(case_id)
    _approval_status[case_id] = "approved" if body.approved else "rejected"
    return {"case_id": case_id, "status": _approval_status[case_id], "approver": body.approver}


@app.get("/health")
def health():
    return {"status": "ok"}