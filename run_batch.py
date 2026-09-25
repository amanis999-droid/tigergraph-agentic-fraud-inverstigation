from __future__ import annotations

import csv
from pathlib import Path

from main import load_case, investigate_case


def main() -> None:
    case_pack = Path("case_pack.csv")
    if not case_pack.exists():
        raise FileNotFoundError("case_pack.csv is required to run the benchmark batch.")

    with case_pack.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))

    for row in rows:
        case = load_case(row["case_id"], case_pack)
        investigate_case(case)
        print(f"Processed {case.case_id}")


if __name__ == "__main__":
    main()
