"""Build results/ports.csv and the README results table from the agent's own reports (ports/*/report.json).

Never edit either by hand. Usage: python scripts/ports_csv.py [ports_dir]
"""
import csv
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIELDS = ["library", "version", "build_system", "arch", "build_result", "tests_passed", "tests_total",
          "patches", "patches_by_rule", "patches_by_model", "rounds", "minutes", "target", "finished", "note"]


def rows(ports: Path) -> list[dict]:
    out = []
    for f in sorted(ports.glob("*/report.json")):
        r = json.loads(f.read_text(encoding="utf-8"))
        if r["arch"] == "host":
            continue  # self-tests with the host compiler are not QNX ports
        r["patches"] = r["patches_kept"]
        if not r["tests_ran"]:
            r["tests_passed"] = r["tests_total"] = ""  # not run is not the same as 0 of 0
        out.append({k: r.get(k, "") for k in FIELDS})
    return out


def readme_table(data: list[dict]) -> str:
    lines = ["| Library | Version | Build | Tests on QNX 8.0 | Patches (rule / model) | Minutes | Note |",
             "|---|---|---|---|---|---|---|"]
    for r in data:
        tests = ("not run" if r["tests_total"] == "" else "none built" if r["tests_total"] == 0
                 else f"{r['tests_passed']}/{r['tests_total']}")
        lines.append(f"| [{r['library']}](ports/{r['library']}/REPORT.md) | {r['version']} | {r['build_result']} "
                     f"| {tests} | {r['patches']} ({r['patches_by_rule']} / {r['patches_by_model']}) "
                     f"| {r['minutes']} | {r.get('note', '')} |")
    return "\n".join(lines)


def main():
    ports = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "ports"
    data = rows(ports)
    dest = ROOT / "results" / "ports.csv"
    with dest.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(data)
    readme = ROOT / "README.md"
    text = readme.read_text(encoding="utf-8")
    text = re.sub(r"(<!-- results:start -->\n).*?(\n<!-- results:end -->)",
                  lambda m: m[1] + readme_table(data) + m[2], text, flags=re.S)
    readme.write_text(text, encoding="utf-8", newline="\n")
    built = sum(r["build_result"] == "built" for r in data)
    tested = [r for r in data if r["tests_total"] != ""]
    print(f"{len(data)} libraries, {built} built for QNX 8.0; tests ran for {len(tested)}: "
          f"{sum(r['tests_passed'] for r in tested)}/{sum(r['tests_total'] for r in tested)} passed -> {dest}")


if __name__ == "__main__":
    main()
