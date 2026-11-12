"""Append one weekly upstream-HEAD run to results/head/history.csv, from the reports it wrote.

    python3 scripts/head_history.py ports-head

Run by .github/workflows/weekly-head.yml after `run_campaign.py --head --no-tests`. One row per library per run:
which upstream commit was built and whether it still builds for QNX 8.0, and with how many QNX changes.
"""
import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / "results" / "head" / "history.csv"
COLUMNS = ["run", "library", "branch", "commit", "arch", "build_result", "rounds", "patches", "minutes"]


def rows(ports: Path, run: str) -> list[dict]:
    out = []
    for f in sorted(ports.glob("*/report.json")):
        r = json.loads(f.read_text(encoding="utf-8"))
        out.append({"run": run, "library": r["library"], "branch": r["version"], "commit": (r.get("commit") or "")[:12],
                    "arch": r["arch"], "build_result": r["build_result"], "rounds": r.get("rounds", 0),
                    "patches": r.get("patches_kept", 0), "minutes": r.get("minutes", "")})
    return out


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    new = rows(Path(argv[0]), datetime.now(timezone.utc).strftime("%Y-%m-%d"))
    DEST.parent.mkdir(parents=True, exist_ok=True)
    first = not DEST.exists()
    with DEST.open("a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, COLUMNS)
        if first:
            w.writeheader()
        w.writerows(new)
    built = sum(r["build_result"] == "built" for r in new)
    print(f"{new[0]['run'] if new else '-'}: {built} of {len(new)} libraries build at upstream HEAD -> {DEST}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
