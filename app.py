from __future__ import annotations

import csv
import json
import os
import socket
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parent
CASE_PACK_PATH = ROOT / "case_pack.csv"
OUTPUT_DIR = ROOT / "cases"
HOST = os.environ.get("HOST", "127.0.0.1")
DEFAULT_PORT = int(os.environ.get("PORT", "8000"))


def find_available_port(start_port: int) -> int:
    port = start_port
    while True:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                sock.bind((HOST, port))
                return port
            except OSError:
                port += 1


def list_cases() -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []
    if not CASE_PACK_PATH.exists():
        return cases

    with CASE_PACK_PATH.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            case_id = (row.get("case_id") or "").strip()
            trigger_text = (row.get("trigger_text") or "").strip()
            if not case_id:
                continue
            cases.append(
                {
                    "case_id": case_id,
                    "trigger_text": trigger_text,
                    "has_answer": (OUTPUT_DIR / f"{case_id}.json").exists(),
                }
            )
    return cases


def read_saved_answer(case_id: str) -> dict[str, Any]:
    path = OUTPUT_DIR / f"{case_id}.json"
    if not path.exists():
        raise FileNotFoundError(f"No saved answer for {case_id}")
    return json.loads(path.read_text(encoding="utf-8"))


def build_dashboard_html() -> str:
    return """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>TigerGraph Fraud Investigation Dashboard</title>
  <style>
    :root {
      color-scheme: light dark;
      --bg: #0f172a;
      --panel: #111827;
      --panel-alt: #1f2937;
      --text: #e5e7eb;
      --muted: #9ca3af;
      --accent: #60a5fa;
      --good: #34d399;
      --warn: #fbbf24;
      --bad: #f87171;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: Arial, sans-serif;
      background: var(--bg);
      color: var(--text);
    }
    .wrap {
      max-width: 1100px;
      margin: 32px auto;
      padding: 20px;
    }
    .panel {
      background: var(--panel);
      border: 1px solid rgba(255,255,255,0.08);
      border-radius: 12px;
      padding: 20px;
      margin-bottom: 18px;
      box-shadow: 0 4px 12px rgba(0,0,0,0.12);
    }
    h1 { margin-top: 0; }
    .controls {
      display: flex;
      flex-wrap: wrap;
      gap: 12px;
      align-items: center;
    }
    select, button {
      font: inherit;
      padding: 10px 14px;
      border-radius: 8px;
      border: 1px solid rgba(255,255,255,0.1);
    }
    select {
      min-width: min(650px, 100%);
      background: var(--panel-alt);
      color: var(--text);
    }
    button {
      background: var(--accent);
      color: #08111f;
      font-weight: 600;
      cursor: pointer;
    }
    button.secondary {
      background: transparent;
      color: var(--text);
    }
    pre {
      white-space: pre-wrap;
      word-break: break-word;
      background: rgba(0,0,0,0.18);
      border-radius: 10px;
      padding: 16px;
      overflow: auto;
      max-height: 560px;
    }
    .small { color: var(--muted); font-size: 0.95rem; }
  </style>
</head>
<body>
  <div class="wrap">
    <div class="panel">
      <h1>TigerGraph Fraud Investigation</h1>
      <div class="small">Local dashboard for benchmark case review and investigation runs.</div>
    </div>

    <div class="panel">
      <div class="controls">
        <select id="case"></select>
        <button id="review">Review saved answer</button>
        <button id="run" class="secondary">Run investigation</button>
      </div>
      <div class="small" id="status" style="margin-top: 12px;">Loading available cases…</div>
    </div>

    <div class="panel">
      <pre id="output">{
  "status": "idle"
}</pre>
    </div>
  </div>

  <script>
    const el = {
      case: document.getElementById('case'),
      review: document.getElementById('review'),
      run: document.getElementById('run'),
      status: document.getElementById('status'),
      output: document.getElementById('output')
    };

    function esc(value) {
      return String(value)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
    }

    async function loadCases() {
      const response = await fetch('/api/cases');
      const cases = await response.json();
      el.case.innerHTML = cases.map(c => `<option value="${esc(c.case_id)}">${esc(c.case_id)} · ${c.has_answer ? 'saved answer' : 'not yet saved'} · ${esc(c.trigger_text || '')}</option>`).join('');
      if (cases.length) {
        el.status.textContent = `${cases.length} cases loaded.`;
      }
    }

    async function requestAnswer(url, button, loadingText) {
      const caseId = el.case.value;
      if (!caseId) {
        el.output.textContent = '{\n  "error": "No case selected"\n}';
        return;
      }

      button.disabled = true;
      button.textContent = loadingText.replace('{id}', caseId);
      el.status.textContent = `Working on ${caseId}...`;

      try {
        const response = await fetch(url, {
          method: url.includes('/api/investigate') ? 'POST' : 'GET',
          headers: url.includes('/api/investigate') ? { 'Content-Type': 'application/json' } : {},
          body: url.includes('/api/investigate') ? JSON.stringify({ case_id: caseId }) : undefined
        });
        const payload = await response.json();
        el.output.textContent = JSON.stringify(payload, null, 2);
        el.status.textContent = response.ok ? `Request completed for ${caseId}.` : `Request failed for ${caseId}.`;
      } catch (error) {
        el.output.textContent = JSON.stringify({ error: String(error) }, null, 2);
        el.status.textContent = `Error while processing ${caseId}.`;
      } finally {
        button.disabled = false;
        button.textContent = button.id === 'review' ? 'Review saved answer' : 'Run investigation';
      }
    }

    el.review.onclick = () => requestAnswer(`/api/answers/${encodeURIComponent(el.case.value)}`, el.review, 'Loading saved answer for {id}...');
    el.run.onclick = () => requestAnswer('/api/investigate', el.run, 'Investigating {id}...');

    loadCases().catch((error) => {
      el.output.textContent = JSON.stringify({ error: String(error) }, null, 2);
      el.status.textContent = 'Unable to load case list.';
    });
  </script>
</body>
</html>
"""


class DashboardHandler(BaseHTTPRequestHandler):
    def log_message(self, fmt: str, *args: Any) -> None:
        return

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path
        query = parse_qs(parsed.query)

        if path == "/":
            self._send_html(build_dashboard_html())
            return

        if path == "/api/cases":
            self._send_json(list_cases())
            return

        if path == "/api/status":
            self._send_json({
                "status": "ok",
                "case_count": len(list_cases()),
                "has_cases": len(list_cases()) > 0,
                "output_dir": str(OUTPUT_DIR),
            })
            return

        if path.startswith("/api/answers/"):
            case_id = path.removeprefix("/api/answers/")
            try:
                answer = read_saved_answer(case_id)
                self._send_json(answer)
            except FileNotFoundError:
                self._send_json({"error": f"No saved answer for {case_id}"}, status=404)
            except Exception as exc:  # pragma: no cover - defensive
                self._send_json({"error": str(exc)}, status=500)
            return

        self._send_json({"error": "Not found"}, status=404)

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path

        if path != "/api/investigate":
            self._send_json({"error": "Not found"}, status=404)
            return

        try:
            length = int(self.headers.get("Content-Length", "0"))
            body = self.rfile.read(length).decode("utf-8") if length else ""
            payload = json.loads(body) if body.strip() else {}
        except Exception as exc:  # pragma: no cover - defensive
            self._send_json({"error": f"Invalid JSON: {exc}"}, status=400)
            return

        case_id = (payload.get("case_id") or parse_qs(parsed.query).get("case_id", [""])[0] or "").strip()
        if not case_id:
            self._send_json({"error": "A case_id is required"}, status=400)
            return

        try:
            from main import investigate_case, load_case

            case = load_case(case_id)
            result = investigate_case(case)
            self._send_json(result)
        except Exception as exc:  # pragma: no cover - defensive
            self._send_json({"error": str(exc)}, status=500)

    def _send_json(self, payload: Any, status: int = 200) -> None:
        data = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _send_html(self, content: str) -> None:
        data = content.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


if __name__ == "__main__":
    PORT = find_available_port(DEFAULT_PORT)
    server = ThreadingHTTPServer((HOST, PORT), DashboardHandler)
    print(f"Serving fraud dashboard on http://{HOST}:{PORT}")
    server.serve_forever()
