"""Port every crate in crates.yaml to QNX 8.0 and write results/crates.csv.

    source ~/qnx800/qnxsdp-env.sh
    python3 scripts/run_crates.py [--arch aarch64le --target root@172.31.1.12] [--no-tests] [--only a,b]

Each crate's report, build log and test output land in ports-rust[-<arch>]/<crate>/.
"""
import argparse
import csv
import json
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from qnx_porter import crate  # noqa: E402
from qnx_porter.target import Target  # noqa: E402

COLUMNS = ["crate", "version", "arch", "rust_target", "build_result", "tests_passed", "tests_total",
           "tests_ignored", "test_binaries", "minutes", "note", "first_error"]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--crates", default=str(ROOT / "crates.yaml"))
    ap.add_argument("--arch")
    ap.add_argument("--target", help="user@host[:port], or 'none' to build only")
    ap.add_argument("--no-tests", action="store_true")
    ap.add_argument("--only", help="comma-separated crate names")
    a = ap.parse_args(argv)
    c = yaml.safe_load(Path(a.crates).read_text(encoding="utf-8"))
    arch = a.arch or c["arch"]
    spec = a.target or c.get("target")
    target = None if a.no_tests or not spec or spec == "none" else Target.parse(spec, c.get("target_dir", "/data/qnx-porter"))
    if target:
        print(f"target: {target.uname() or 'NOT REACHABLE'}")
    out = ROOT / ("ports-rust" if arch == "x86_64" else f"ports-rust-{arch}")
    todo = [x for x in c["crates"] if not a.only or x["name"] in a.only.split(",")]
    for i, x in enumerate(todo, 1):
        print(f"\n=== [{i}/{len(todo)}] {x['name']} {x['version']} ===", flush=True)
        crate.port(x["name"], str(x["version"]), out, arch=arch, target=target)
    rows = []
    for p in sorted(out.glob("*/report.json")):
        r = json.loads(p.read_text(encoding="utf-8"))
        rows.append({**{k: r.get(k, "") for k in COLUMNS}, "first_error": (r.get("errors") or [""])[0]})
    dest = ROOT / "results" / ("crates.csv" if arch == "x86_64" else f"crates-{arch}.csv")
    with dest.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, COLUMNS)
        w.writeheader()
        w.writerows(rows)
    built = [r for r in rows if r["build_result"] == "built"]
    ran = [r for r in rows if r["tests_total"]]
    print(f"\n{arch}: {len(rows)} crates, {len(built)} built for QNX 8.0; tests ran for {len(ran)} "
          f"(at least one test each): {sum(r['tests_passed'] for r in ran)}/{sum(r['tests_total'] for r in ran)} passed")
    print(f"-> {dest}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
