"""Real-time readiness report for every port: static hazard scan + latency on the QNX target.

For each ports/<lib>/ with a work tree, writes ports/<lib>/rt.json:
  scan   - qnx_porter.rt.scan() of the library's own sources (counts and first places, per hazard)
  bench  - qnx_porter.rt_bench: one core call (bench/specs.yaml), idle / loaded / loaded + runmask isolation,
           min / median / p99 / max microseconds, measured on the target (only for libraries with a spec)
  score  - static score, minus up to 30 for jitter when there is a benchmark
and results/rt.csv with one row per library.

Usage (SDP sourced, target running, after scripts/run_campaign.py):
    python3 scripts/rt_report.py [--only lib,lib] [--no-bench]
"""
import argparse
import csv
import json
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from qnx_porter import qnx, rt, rt_bench  # noqa: E402
from qnx_porter.target import Target  # noqa: E402

FIELDS = ["library", "arch", "static_score", "heap", "blocking_io", "sleep", "process", "signals", "threads",
          "mutexes", "bench_call", "idle_median_us", "idle_p99_us", "loaded_median_us", "loaded_p99_us",
          "loaded_max_us", "isolated_p99_us", "isolated_max_us", "rt_score"]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--ports", default=str(ROOT / "ports"))
    ap.add_argument("--only")
    ap.add_argument("--no-bench", action="store_true")
    ap.add_argument("--target", default="root@172.31.1.11")
    ap.add_argument("--n", type=int, default=20000, help="calls per run")
    a = ap.parse_args(argv)
    specs = yaml.safe_load((ROOT / "bench" / "specs.yaml").read_text(encoding="utf-8"))
    env = None if a.no_bench else qnx.sdp_env()
    t = Target.parse(a.target)
    rows = []
    for rep in sorted(Path(a.ports).glob("*/report.json")):
        r = json.loads(rep.read_text(encoding="utf-8"))
        lib, d = r["library"], rep.parent
        if a.only and lib not in a.only.split(","):
            continue
        src, bdir = d / "work" / "src", d / "work" / "build"
        if not src.is_dir():
            print(f"{lib}: no work tree, skipped", file=sys.stderr)
            continue
        out = {"library": lib, "arch": r["arch"], "scan": rt.scan(src), "bench": None}
        spec = specs.get(lib)
        if spec and not a.no_bench and r["build_result"] == "built":
            arch = qnx.ARCHES[r["arch"]]
            ok, err = rt_bench.compile_bench(spec, src, bdir, d / "work" / "rt-bench", env, arch.qcc_target)
            out["bench"] = (dict(rt_bench.run_bench(t, d / "work" / "rt-bench" / "bench", lib, a.n), call=spec["what"])
                            if ok else {"error": "harness did not compile: " + err[-400:], "call": spec["what"]})
        out["score"] = rt_bench.rt_score(out["scan"]["static_score"], out["bench"])
        if out["score"] is None:
            out["score"] = out["scan"]["static_score"]
            out["score_basis"] = "static scan only"
        else:
            out["score_basis"] = "static scan and latency on the QNX target"
        (d / "rt.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
        b = out["bench"] or {}
        g = lambda run, k: (b.get(run) or {}).get(k, "")  # noqa: E731
        rows.append({"library": lib, "arch": r["arch"], "static_score": out["scan"]["static_score"],
                     **{k: v["count"] for k, v in out["scan"]["hazards"].items()},
                     "bench_call": b.get("call", ""), "idle_median_us": g("idle", "median_us"),
                     "idle_p99_us": g("idle", "p99_us"), "loaded_median_us": g("loaded", "median_us"),
                     "loaded_p99_us": g("loaded", "p99_us"), "loaded_max_us": g("loaded", "max_us"),
                     "isolated_p99_us": g("loaded_isolated", "p99_us"), "isolated_max_us": g("loaded_isolated", "max_us"),
                     "rt_score": out["score"]})
        print(f"{lib:16s} score {out['score']:3d}  " + (f"p99 idle/loaded/isolated {g('idle', 'p99_us')}/"
              f"{g('loaded', 'p99_us')}/{g('loaded_isolated', 'p99_us')} us" if b and "idle" in b else
              (b.get("error", "")[:80] if b else "static only")))
    dest = ROOT / "results" / "rt.csv"
    with dest.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)
    print(f"{len(rows)} libraries -> {dest}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
