"""Real-time readiness report: a static hazard scan of each port's sources, and call latency on a QNX target.

Reads the campaign's port folders: <ports>/<lib>/report.json, work/src (sources) and work/build (static
archives). A library without work/src is reported as "sources absent", not skipped silently.

  --scan-only   static scan only (qnx_porter.rt.scan): no SDP, no target. Writes results/rt_scan.csv.
  (default)     the scan, plus one core call per library (bench/specs.yaml) built with qcc and timed on the
                target: idle, under load, and under load with runmask isolation (qnx_porter.rt_bench).
                Writes ports[-<arch>]/<lib>/rt.json, results/rt_scan.csv and results/rt.csv.
CSV rows are merged by (library, arch), so --only and a second --arch keep the other rows.

Usage:
    python3 scripts/rt_report.py --scan-only [--ports DIR] [--only lib,lib]
    source ~/qnx800/qnxsdp-env.sh
    python3 scripts/rt_report.py --target root@172.31.1.11 [--arch x86_64] [--ports DIR] [--only lib,lib] [--n 20000]
"""
import argparse
import csv
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from qnx_porter import qnx, rt, rt_bench  # noqa: E402
from qnx_porter.target import Target  # noqa: E402

SCAN_FIELDS = ["library", "arch", "commit", "sources", "files", "lines", *rt.CATEGORIES, "static_score"]
BENCH_FIELDS = ["library", "arch", "commit", "platform", "target", "iterations", "cpus", "call",
                *(f"{run}_{s}_us" for run in rt_bench.RUNS for s in rt_bench.STATS),
                "static_score", "rt_score", "error"]
MEASURED = (f"Time of one library call (ClockCycles() before and after), {{n}} timed calls after "
            f"{rt_bench.WARMUP} untimed warm-up calls, in a SCHED_FIFO priority {rt_bench.PRIORITY} thread. "
            f"Three runs: idle (nothing else of ours running); loaded (one SCHED_RR priority "
            f"{rt_bench.LOAD_PRIORITY} thread per CPU churning malloc/memset/free); loaded_isolated (the same "
            f"load, measured thread on CPU 0 and load on the other CPUs via ThreadCtl(_NTO_TCTL_RUNMASK)). "
            f"Statistics per run: min, median, p99, p99.9, max in microseconds; max is the worst case seen "
            f"in that run, not a bound.")
TIMING = {
    "qemu": "Measured on a QEMU virtual machine. Absolute times and jitter include the emulator and the host "
            "operating system: they are NOT representative of QNX on hardware. Compare runs and libraries "
            "with each other, not with hardware figures.",
    "hardware": "Measured on QNX hardware; the figures hold for this board, clock and configuration only.",
}


def merge_csv(dest: Path, fields: list[str], rows: list[dict]) -> None:
    """Write rows into dest, keeping existing rows for other (library, arch) keys."""
    key = lambda r: (r["library"], r["arch"])  # noqa: E731
    old = {}
    if dest.exists():
        with dest.open(newline="", encoding="utf-8") as f:
            old = {key(r): r for r in csv.DictReader(f)}
    old.update({key(r): r for r in rows})
    dest.parent.mkdir(parents=True, exist_ok=True)
    with dest.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(old[k] for k in sorted(old, key=lambda k: (k[0].lower(), k[1])))


def scan_row(lib: str, arch: str, commit: str, scan: dict | None) -> dict:
    if scan is None:
        return {"library": lib, "arch": arch, "commit": commit, "sources": "absent"}
    return {"library": lib, "arch": arch, "commit": commit, "sources": "scanned", "files": scan["files"],
            "lines": scan["lines"], **{k: v["count"] for k, v in scan["hazards"].items()},
            "static_score": scan["static_score"]}


def bench_row(out: dict) -> dict:
    b = out["bench"] or {}
    runs = b.get("runs") or {}
    row = {"library": out["library"], "arch": out["arch"], "commit": out["commit"], "platform": b.get("platform", ""),
           "target": b.get("target", ""), "iterations": b.get("iterations", ""), "call": b.get("call", ""),
           "cpus": (runs.get("idle") or {}).get("cpus", ""), "static_score": out["static_score"],
           "rt_score": out["rt_score"] if out["rt_score"] is not None else "",
           "error": b.get("error") or "; ".join(f"{k}: {v['error']}" for k, v in runs.items() if "error" in v)}
    for run in rt_bench.RUNS:
        for s in rt_bench.STATS:
            row[f"{run}_{s}_us"] = (runs.get(run) or {}).get(f"{s}_us", "")
    return row


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--arch", default="x86_64", choices=sorted(qnx.ARCHES))
    ap.add_argument("--ports", help="the campaign's port folders, with work/ trees (default: ports/ for x86_64, "
                                    "ports-<arch>/ otherwise)")
    ap.add_argument("--only", help="comma-separated library names")
    ap.add_argument("--scan-only", action="store_true", help="static scan only; needs no SDP and no target")
    ap.add_argument("--target", help="QNX target, user@host[:port] (required unless --scan-only)")
    ap.add_argument("--target-dir", default="/data/qnx-porter", help="scratch folder on the target")
    ap.add_argument("--platform", default="qemu", choices=sorted(TIMING), help="what the target is (default: qemu)")
    ap.add_argument("--n", type=int, default=20000, help="timed calls per run (default 20000, at least 1000)")
    a = ap.parse_args(argv)
    if not a.scan_only and not a.target:
        ap.error("--target user@host[:port] is required unless --scan-only")
    if a.n < 1000:
        ap.error("--n must be at least 1000 (p99.9 needs it)")
    port_dir = "ports" if a.arch == "x86_64" else f"ports-{a.arch}"
    ports = Path(a.ports) if a.ports else ROOT / port_dir
    reports = [json.loads(p.read_text(encoding="utf-8")) | {"_dir": p.parent}
               for p in sorted(ports.glob("*/report.json"))]
    reports = [r for r in reports if r.get("arch") == a.arch]
    if a.only:
        want = set(a.only.split(","))
        unknown = want - {r["library"] for r in reports}
        if unknown:
            ap.error(f"not in {ports} for {a.arch}: {', '.join(sorted(unknown))}")
        reports = [r for r in reports if r["library"] in want]
    if not reports:
        ap.error(f"no {a.arch} report.json under {ports}")

    if not a.scan_only:
        specs = yaml.safe_load((ROOT / "bench" / "specs.yaml").read_text(encoding="utf-8"))
        env, t = qnx.sdp_env(), Target.parse(a.target, a.target_dir)
        uname = t.uname()
        if not uname:
            sys.exit(f"{a.target} did not answer `uname -a` over ssh")
        head = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "--short", "HEAD"], capture_output=True,
                              text=True).stdout.strip()
    scan_rows, bench_rows = [], []
    for r in reports:
        lib, d, commit = r["library"], r["_dir"], r.get("commit", "")
        src, bdir = d / "work" / "src", d / "work" / "build"
        scan = rt.scan(src, keep=lib) if src.is_dir() else None
        scan_rows.append(scan_row(lib, a.arch, commit, scan))
        if a.scan_only:
            print(f"{lib:16s} " + (f"static score {scan['static_score']:3d}  " + " ".join(
                f"{k}={v['count']}" for k, v in scan["hazards"].items()) if scan else "sources absent"))
            continue

        out = {"library": lib, "arch": a.arch, "commit": commit, "generated": datetime.now(timezone.utc)
               .isoformat(timespec="seconds"), "qnx_porter_commit": head,
               "scan": scan if scan else {"error": "sources absent: no work/src"}, "bench": None}
        spec = specs.get(lib)
        if not spec:
            out["bench"] = {"error": "no call spec in bench/specs.yaml"}
        elif r.get("build_result") != "built":
            out["bench"] = {"error": f"library not built ({r.get('build_result')})", "call": spec["what"]}
        elif not bdir.is_dir():
            out["bench"] = {"error": "build tree absent: no work/build", "call": spec["what"]}
        else:
            bench_out = ROOT / "build" / "rt-bench" / a.arch / lib
            ok, err = rt_bench.compile_bench(spec, src, bdir, bench_out, env, qnx.ARCHES[a.arch].qcc_target)
            out["bench"] = {"call": spec["what"], "target": uname, "platform": a.platform, "iterations": a.n,
                            "measured": MEASURED.format(n=a.n), "timing_note": TIMING[a.platform]}
            if not ok:
                out["bench"]["error"] = "harness did not compile: " + err[-400:]
            else:
                try:
                    out["bench"]["runs"] = rt_bench.run_bench(t, bench_out / "bench", lib, a.n)
                except (subprocess.SubprocessError, OSError) as e:  # one library's failure does not stop the rest
                    out["bench"]["error"] = f"could not run on the target: {e}"[:400]
        out["static_score"] = scan["static_score"] if scan else None
        out["rt_score"] = rt_bench.rt_score(scan["static_score"], (out["bench"] or {}).get("runs")) if scan else None
        out["score_basis"] = ("static scan and latency on the QNX target" if out["rt_score"] is not None else
                              "static scan only" if scan else "none: sources absent")
        dest = ROOT / port_dir / lib
        dest.mkdir(parents=True, exist_ok=True)
        (dest / "rt.json").write_text(json.dumps(out, indent=1) + "\n", encoding="utf-8")
        row = bench_row(out)
        if spec:  # results/rt.csv holds the benchmarked libraries; the others have their scan in rt.json
            bench_rows.append(row)
        print(f"{lib:16s} " + (row["error"][:100] if row["error"] else
                               f"p99 idle/loaded/isolated {row['idle_p99_us']}/{row['loaded_p99_us']}/"
                               f"{row['loaded_isolated_p99_us']} us, max loaded {row['loaded_max_us']} us"))

    merge_csv(ROOT / "results" / "rt_scan.csv", SCAN_FIELDS, scan_rows)
    print(f"{len(scan_rows)} libraries scanned ({sum(r['sources'] == 'scanned' for r in scan_rows)} with sources)"
          f" -> results/rt_scan.csv", file=sys.stderr)
    if bench_rows:
        merge_csv(ROOT / "results" / "rt.csv", BENCH_FIELDS, bench_rows)
        print(f"{len(bench_rows)} libraries -> results/rt.csv and {port_dir}/<lib>/rt.json", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
