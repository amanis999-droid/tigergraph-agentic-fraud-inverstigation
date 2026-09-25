# TigerGraph Agentic Fraud Investigation

A fraud-investigation benchmark and agent workflow that combines TigerGraph graph retrieval, policy-driven scoring, and structured case output generation for card and account takeover scenarios.

This project is designed to investigate suspicious transactions by gathering evidence from graph tools and benchmark data, validating case history, scoring the fraud risk, and producing a machine-readable investigation result in a schema-driven format.

## Overview

The workflow is built around:

- a case pack of flagged transactions and customer context
- graph-backed evidence retrieval via TigerGraph/MCP tools
- policy-based fraud reasoning and stop conditions
- SAR and recommended-action logic
- JSON case outputs saved under the `cases/` directory

The implementation is meant to mimic a real financial investigation process: gather facts, reject invalid or placeholder IDs, assess fraud probability from policy rules, and produce a final answer that follows a strict schema.

## Key capabilities

- Investigates suspicious transactions using case metadata and graph evidence
- Uses closed-case history to validate prior case IDs and avoid invalid benchmark references
- Filters placeholder or unsupported evidence before final output assembly
- Generates policy-aligned fraud probability, pattern classification, and actions
- Saves benchmark-ready outputs for each case in the `cases/` folder
- Includes validation logic and regression checks for benchmark integrity

## Project structure

```text
.
├── README.md
├── app.py
├── main.py
├── run_batch.py
├── policy.py
├── schema.py
├── mcp_tools.py
├── requirements.txt
├── case_pack.csv
├── transactions.csv
├── closed_cases_history.csv
├── identity.csv
├── cases/
├── docs/
├── scripts/
├── tigergraph/
├── tests/
└── .env.example (if used locally)
```

## How it works

1. A case is loaded from the benchmark case pack.
2. Relevant customer, transaction, and graph evidence is collected.
3. Policy logic evaluates patterns such as suspicious amounts, region mismatches, unusual channels, customer denials, and closed-case similarities.
4. Invalid or placeholder prior-case IDs are filtered out.
5. A final structured answer is produced according to the project schema.
6. The result is saved as JSON under `cases/`.

## Local setup

### 1) Clone the repository

```bash
git clone https://github.com/<your-username>/tigergraph-agentic-fraud-inverstigation.git
cd tigergraph-agentic-fraud-inverstigation
```

### 2) Create a virtual environment

#### Windows

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

#### macOS / Linux

```bash
python -m venv .venv
source .venv/bin/activate
```

### 3) Install dependencies

```bash
pip install -r requirements.txt
```

### 4) Configure environment variables

Create a local `.env` file in the project root:

```env
GROQ_API_KEY=your_api_key_here
```

If your setup uses a different model or runtime behavior, you may also define optional settings such as:

```env
GROQ_MODEL=openai/gpt-oss-20b
GROQ_FALLBACK_MODEL=qwen/qwen3.8-27b
GROQ_MAX_TOOL_ROUNDS=5
ALLOW_CSV_FALLBACK=true
```

## Run the project

### Run the benchmark batch

```bash
python run_batch.py
```

This generates or updates the case output files in `cases/`.

### Run a single investigation flow

```bash
python main.py
```

### Run validation tests

```bash
python -m pytest -q
```

## Benchmark data notes

This project relies on benchmark CSV files and graph-like evidence sources. If the repository is cloned in a fresh environment:

- ensure the benchmark datasets are present locally
- ensure the repo has access to the required data files
- if `transactions.csv` is large, use Git LFS as needed for your hosting setup

Example for Git LFS:

```bash
git lfs install
git lfs track "transactions.csv"
git add .gitattributes transactions.csv
git commit -m "Track benchmark data with Git LFS"
```

## Output format

Case outputs are stored as JSON and follow a structured investigation schema. They include fields for:

- case metadata
- evidence collection
- policy-derived fraud indicators
- recommended actions
- SAR decisions
- prior-case validation and final verdict summary

The objective is to keep the output both readable and machine-checkable.

## Validation and quality checks

The project includes checks to ensure:

- no invalid prior-case IDs are generated
- no placeholder graph evidence is passed into final answers
- structured output remains within the expected schema
- case files are cleaned and consistent with the benchmark rules

## License

This project is intended for research and benchmark use. Add your project license here if you plan to publish it publicly.

## Contributing

Contributions are welcome. If you are improving detection logic, benchmark validation, or evidence quality, please:

1. create a feature branch
2. add or update tests for the behavior you change
3. run the validation suite
4. submit a pull request with a clear summary of the fix

## Notes

This workflow is optimized for a controlled fraud-investigation benchmark and emphasizes evidence quality, schema compliance, and policy-grounded scoring over free-form model output.

