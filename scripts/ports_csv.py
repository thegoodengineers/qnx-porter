"""Build results/ports.csv and the README results table from the agent's own reports (ports/*/report.json).

Never edit either by hand. Usage: python scripts/ports_csv.py [ports_dir]
"""
import csv
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
FIELDS = ["library", "version", "build_system", "arch", "build_result", "tests_passed", "tests_total",
          "patches", "patches_by_rule", "patches_by_model", "rounds", "minutes", "target", "finished", "note",
          "on_oss_qnx_com", "tests_not_runnable"]


def rows(ports: Path) -> list[dict]:
    listed_file = ROOT / "results" / "oss_listed.json"  # written by run_campaign.py from oss.qnx.com
    listed = set(json.loads(listed_file.read_text())) if listed_file.exists() else None
    out = []
    for f in sorted(ports.glob("*/report.json"), key=lambda p: p.parent.name):  # case-sensitive on every OS
        r = json.loads(f.read_text(encoding="utf-8"))
        if r["arch"] == "host":
            continue  # self-tests with the host compiler are not QNX ports
        r["patches"] = r["patches_kept"]
        if not r["tests_ran"]:
            r["tests_passed"] = r["tests_total"] = ""  # not run is not the same as 0 of 0
        r["on_oss_qnx_com"] = "" if listed is None else ("yes" if r["library"] in listed else "no")
        nr = r.get("tests_not_runnable") or []
        r["tests_not_runnable"] = "; ".join(sorted({f"{sum(x['needs'] == n for x in nr)} need {n}"
                                                   for n in {x["needs"] for x in nr}}))
        out.append({k: r.get(k, "") for k in FIELDS})
    return out


def readme_table(data: list[dict]) -> str:
    lines = ["| Library | Version | Arch | Build | Tests on QNX 8.0 | Patches (rule / model) | Minutes | Note |",
             "|---|---|---|---|---|---|---|---|"]
    for r in data:
        tests = ("not run" if r["tests_total"] == "" else "none built" if r["tests_total"] == 0
                 else f"{r['tests_passed']}/{r['tests_total']}")
        folder = "ports" if r["arch"] == "x86_64" else f"ports-{r['arch']}"
        lines.append(f"| [{r['library']}]({folder}/{r['library']}/REPORT.md) | {r['version']} | {r['arch']} | {r['build_result']} "
                     f"| {tests} | {r['patches']} ({r['patches_by_rule']} / {r['patches_by_model']}) "
                     f"| {r['minutes']} | {r.get('note', '')} |")
    return "\n".join(lines)


def headline(data: list[dict]) -> str:
    """One sentence per architecture, from the same rows as the CSV."""
    parts = []
    for arch in sorted({r["arch"] for r in data}):
        rs = [r for r in data if r["arch"] == arch]
        tested = [r for r in rs if r["tests_total"] not in ("", 0)]
        parts.append(f"{arch}: {sum(r['build_result'] == 'built' for r in rs)} of {len(rs)} libraries built for QNX 8.0; "
                     f"{sum(r['tests_passed'] for r in tested)} of {sum(r['tests_total'] for r in tested)} of their own "
                     f"tests passed on a QNX 8.0 target ({len(tested)} libraries with tests that ran); "
                     f"{sum(int(r['patches']) for r in rs)} patches, {sum(int(r['patches_by_rule']) for r in rs)} by rules")
        new = [r for r in rs if r.get("on_oss_qnx_com") == "no"]
        if new:
            parts[-1] += (f" ({sum(r['build_result'] == 'built' for r in new)} of the {len(new)} libraries "
                          f"oss.qnx.com does not list built)")
    return "; ".join(parts) + "."


def main():
    arg_dirs = [Path(a) for a in sys.argv[1:] if not a.startswith("--")]
    dirs = arg_dirs if arg_dirs else [ROOT / "ports", ROOT / "ports-aarch64le"]
    data = [r for d in dirs for r in rows(d)]
    dest = ROOT / "results" / "ports.csv"
    with dest.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(data)
    readme = ROOT / "README.md"
    text = readme.read_text(encoding="utf-8")
    text = re.sub(r"(<!-- results:start -->\n).*?(\n<!-- results:end -->)",
                  lambda m: m[1] + readme_table(data) + m[2], text, flags=re.S)
    text = re.sub(r"(<!-- headline:start -->).*?(<!-- headline:end -->)",
                  lambda m: m[1] + headline(data) + m[2], text, flags=re.S)
    readme.write_text(text, encoding="utf-8", newline="\n")
    sys.path.insert(0, str(ROOT))
    from qnx_porter.target import RESULT_LINE, junit_from_log
    for log in (p for d in dirs for p in d.glob("*/logs/tests.log")):  # JUnit beside every per-test log
        text = log.read_text(encoding="utf-8", errors="replace")
        if any(RESULT_LINE.match(ln) for ln in text.splitlines()):
            log.with_name("tests.junit.xml").write_text(junit_from_log(text), encoding="utf-8", newline="\n")
    print(summary(data))
    print(f"-> {dest}")
    if "--intelligence" in sys.argv:
        from qnx_porter import intelligence
        for d in dirs:
            if d.exists():
                reports = [json.loads(p.read_text(encoding="utf-8")) for p in d.glob("*/report.json")]
                arch = reports[0].get("arch", "x86_64") if reports else "x86_64"
                json_name = f"campaign_intelligence{'_' + arch if arch != 'x86_64' else ''}.json"
                intel_dest = ROOT / "results" / json_name
                intelligence.save_campaign_intelligence(d, intel_dest, arch=arch)
                print(f"-> {intel_dest}")


def summary(data: list[dict]) -> str:
    """One line per architecture; video/render.py reads these lines from the demo recording."""
    lines = []
    for arch in sorted({r["arch"] for r in data}):
        rs = [r for r in data if r["arch"] == arch]
        built = sum(r["build_result"] == "built" for r in rs)
        tested = [r for r in rs if r["tests_total"] not in ("", 0)]  # same count as the headline
        lines.append(f"{arch}: {len(rs)} libraries, {built} built for QNX 8.0; tests ran for {len(tested)} (at least one test each): "
                     f"{sum(r['tests_passed'] for r in tested)}/{sum(r['tests_total'] for r in tested)} passed")
    return "\n".join(lines)


if __name__ == "__main__":
    main()
