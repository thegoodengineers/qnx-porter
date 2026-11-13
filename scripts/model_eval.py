"""What does the model step add over the rules alone? Re-run the libraries the rules could not finish.

Reads the rules-only campaign (ports/*/report.json), picks every library that did not build, re-ports each
with the model step on into ports-model/<lib>/, and writes results/model_eval.csv: rules-only result next
to rules+model result, the model's patches kept and reverted, calls, tokens and time.

Needs QNX_PORTER_API_KEY, QNX_PORTER_MODEL and QNX_PORTER_BASE_URL in the environment (see SETUP.md); stops
with that message if they are missing. Usage:
    source ~/qnx800/qnxsdp-env.sh && python3 scripts/model_eval.py [--only lib,lib] [--max-rounds 25]
"""
import argparse
import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from qnx_porter import agent, llm  # noqa: E402
from qnx_porter.target import Target  # noqa: E402
from run_campaign import for_library, load  # noqa: E402

FIELDS = ["library", "rules_only_build", "rules_only_tests", "rules_model_build", "rules_model_tests",
          "model_patches_kept", "model_patches_reverted", "rule_patches", "model_calls", "model_failed_calls",
          "tokens_in", "tokens_out", "model_seconds", "minutes", "still_failing_on"]


def tests(r: dict) -> str:
    return f"{r['tests_passed']}/{r['tests_total']}" if r.get("tests_ran") else "not run"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--only")
    ap.add_argument("--max-rounds", type=int, default=25)
    ap.add_argument("--no-tests", action="store_true")
    a = ap.parse_args(argv)
    if not llm.configured():
        raise SystemExit("The model step is not configured. Set QNX_PORTER_API_KEY, QNX_PORTER_MODEL and "
                         "QNX_PORTER_BASE_URL in your shell (never in the repository); see SETUP.md.")
    c = load(ROOT / "campaign.yaml")
    libs = {lib["name"]: lib for lib in c["libraries"]}
    target = None if a.no_tests or not c["target"] else Target.parse(c["target"], c["target_dir"])
    rows = []
    for rep in sorted((ROOT / "ports").glob("*/report.json")):
        base = json.loads(rep.read_text(encoding="utf-8"))
        name = base["library"]
        if base["build_result"] == "built" or name not in libs or (a.only and name not in a.only.split(",")):
            continue
        lib = libs[name]
        print(f"=== {name}: rules only ended {base['build_result']}; re-porting with the model step", flush=True)
        r = agent.port(lib["url"], lib["tag"], ROOT / "ports-model", arch=c["arch"],
                       target=for_library(target, lib) if lib["tests"] else None, max_rounds=a.max_rounds, use_llm=True,
                       extra_args=tuple(lib["args"] + lib["arch_args"].get(c["arch"], [])), name=name,
                       note=lib["note"], subdir=lib["subdir"])
        u = r.get("model_usage") or {}
        model = [p for p in r["patches"] if p["source"] == "model"]
        rows.append({"library": name, "rules_only_build": base["build_result"], "rules_only_tests": tests(base),
                     "rules_model_build": r["build_result"], "rules_model_tests": tests(r),
                     "model_patches_kept": sum(p["kept"] for p in model),
                     "model_patches_reverted": sum(not p["kept"] for p in model),
                     "rule_patches": r["patches_by_rule"], "model_calls": u.get("calls", 0),
                     "model_failed_calls": u.get("failed_calls", 0), "tokens_in": u.get("tokens_in", 0),
                     "tokens_out": u.get("tokens_out", 0), "model_seconds": u.get("seconds", 0),
                     "minutes": r["minutes"],
                     "still_failing_on": (r["blocked_on"][0]["error"][:160] if r["blocked_on"] else "")})
        print(f"    rules+model: {r['build_result']}, tests {tests(r)}, model patches kept "
              f"{rows[-1]['model_patches_kept']} / reverted {rows[-1]['model_patches_reverted']}", flush=True)
    dest = ROOT / "results" / "model_eval.csv"
    if dest.exists():  # an --only run replaces its own libraries' rows and keeps the others
        done = {r["library"] for r in rows}
        rows = [r for r in csv.DictReader(dest.open(encoding="utf-8")) if r["library"] not in done] + rows
        rows.sort(key=lambda r: r["library"].lower())
    with dest.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)
    built = sum(r["rules_model_build"] == "built" for r in rows)
    print(f"{len(rows)} libraries the rules could not finish; with the model step {built} built -> {dest}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
