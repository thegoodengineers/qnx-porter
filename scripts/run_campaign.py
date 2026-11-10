"""Port every library in campaign.yaml to QNX 8.0, then write results/ports.csv and the README table.

The day the SDP is installed this is the only command to run:
    source ~/qnx800/qnxsdp-env.sh
    python3 scripts/run_campaign.py

It stops before doing anything if qcc or the QNX target is missing, and says which SETUP.md step fixes it.
Each library's patches, diff (qnx.patch), toolchain file and logs land in ports/<name>/.
"""
import argparse
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from qnx_porter import agent, qnx  # noqa: E402
from qnx_porter.target import Target  # noqa: E402

REQUIRED = ("name", "url", "tag")


def load(path: Path) -> dict:
    c = yaml.safe_load(path.read_text(encoding="utf-8"))
    libs = c.get("libraries") or []
    for lib in libs:
        missing = [k for k in REQUIRED if not lib.get(k)]
        if missing:
            raise SystemExit(f"{path}: library {lib} is missing {', '.join(missing)}")
        lib["tag"] = str(lib["tag"])
        lib["args"] = [str(a) for a in lib.get("args", [])]
    return {"target": c.get("target"), "target_dir": c.get("target_dir", "/data/qnx-porter"),
            "arch": c.get("arch", "x86_64"), "max_rounds": int(c.get("max_rounds", 15)), "libraries": libs}


def preflight(env_source=None) -> dict:
    """The SDP environment, or exit with the SETUP.md step that fixes what is missing."""
    try:
        env = qnx.sdp_env(env_source)
    except SystemExit:
        raise SystemExit("QNX SDP 8.0 not found (no QNX_HOST/QNX_TARGET and no ~/qnx800/qnxsdp-env.sh).\n"
                         "Install it with SETUP.md step 3, then run: source ~/qnx800/qnxsdp-env.sh") from None
    qcc = Path(qnx.tool(env, "qcc"))
    if not qcc.exists():
        raise SystemExit(f"qcc not found at {qcc}. QNX_HOST={env.get('QNX_HOST')} does not hold an SDP 8.0 "
                         "install. See SETUP.md step 3, and run `qnx-porter doctor`.")
    return env


def check_target(t: Target) -> str:
    uname = t.uname()
    if not uname:
        raise SystemExit(f"QNX target {t.host}:{t.port} did not answer over ssh. Start it with SETUP.md step 4 "
                         "(mkqnximage --run=-h), or pass --no-tests to build only.")
    return uname


def already_on_oss(libs: list[dict], names: set, urls: set) -> list[str]:
    """Libraries oss.qnx.com now lists: same package name (or name-<subpackage>) or same upstream URL."""
    def listed(lib):
        n, url = lib["name"].lower(), lib["url"].lower().rstrip("/").removesuffix(".git")
        return url in urls or any(x == n or x.startswith(n + "-") for x in names)
    return [lib["name"] for lib in libs if listed(lib)]


def error_report(out: Path, lib: dict, arch: str, err: str, minutes: float) -> None:
    """A report.json for a library the agent could not even start on, so the CSV still shows it."""
    d = out / lib["name"]
    d.mkdir(parents=True, exist_ok=True)
    (d / "report.json").write_text(json.dumps({
        "library": lib["name"], "url": lib["url"], "version": lib["tag"], "commit": "", "build_system": "",
        "arch": arch, "sdp": "QNX SDP 8.0", "target": "", "build_result": "error", "rounds": 0,
        "tests_passed": 0, "tests_total": 0, "tests_ran": False, "patches_kept": 0, "patches_by_rule": 0,
        "patches_by_model": 0, "patches": [], "blocked_on": [{"kind": "error", "error": err[-2000:], "hint": ""}],
        "minutes": round(minutes, 1), "finished": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }, indent=2), encoding="utf-8")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--campaign", default=str(ROOT / "campaign.yaml"))
    ap.add_argument("--out", default=str(ROOT / "ports"))
    ap.add_argument("--only", help="comma-separated library names")
    ap.add_argument("--no-tests", action="store_true", help="build only, do not use the QNX target")
    ap.add_argument("--no-model", action="store_true", help="deterministic rules only")
    ap.add_argument("--skip-oss-check", action="store_true", help="do not re-check oss.qnx.com first")
    a = ap.parse_args(argv)

    c = load(Path(a.campaign))
    libs = [lib for lib in c["libraries"] if not a.only or lib["name"] in a.only.split(",")]
    preflight()
    target = None
    if c["target"] and not a.no_tests:
        target = Target.parse(c["target"], c["target_dir"])
        print(f"target: {check_target(target)}")
    if not a.skip_oss_check:
        from check_candidates import oss_packages
        ported = already_on_oss(libs, *oss_packages())
        for name in ported:
            print(f"skip {name}: oss.qnx.com lists it now")
        libs = [lib for lib in libs if lib["name"] not in ported]

    out = Path(a.out)
    for i, lib in enumerate(libs, 1):
        print(f"\n=== [{i}/{len(libs)}] {lib['name']} {lib['tag']} ===")
        t0 = time.time()
        try:
            agent.port(lib["url"], lib["tag"], out, arch=c["arch"], target=target, max_rounds=c["max_rounds"],
                       use_llm=not a.no_model, extra_args=tuple(lib["args"]), name=lib["name"])
        except (subprocess.CalledProcessError, OSError, RuntimeError, ValueError) as e:
            print(f"    {lib['name']}: agent error: {e}")
            error_report(out, lib, c["arch"], str(e), (time.time() - t0) / 60)
    subprocess.run([sys.executable, str(ROOT / "scripts" / "ports_csv.py"), str(out)], check=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
